use actix_web::{web, App, HttpResponse, HttpServer, Responder};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use log::{info, error};
use env_logger;
use sp1_sdk::{include_elf, ProverClient, SP1Stdin};

// Include the verification program ELF
pub const VERIFY_ELF: &[u8] = include_elf!("verify-program");

#[derive(Debug, Serialize, Deserialize)]
struct VerificationData {
    verification_file: String,
    json_dicts: Vec<HashMap<String, serde_json::Value>>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ProofResult {
    verification_result: bool,
    proof: String,
    verification_key: String,
    public_values: String,
}

async fn process_data(data: web::Json<VerificationData>) -> impl Responder {
    info!("=== GCP Server - Received New Request ===");
    info!("Verification file content:");
    info!("{}", data.verification_file);
    info!("\nJSON dictionaries received:");
    info!("{}", serde_json::to_string_pretty(&data.json_dicts).unwrap());
    
    // Setup the prover client
    let client = ProverClient::from_env();
    
    // Setup the inputs for the proof
    let mut stdin = SP1Stdin::new();
    
    // Write verification conditions
    stdin.write(&data.verification_file);
    
    // Write JSON data
    let json_data = serde_json::to_string(&data.json_dicts).unwrap();
    stdin.write(&json_data);
    
    // Generate the proving and verification keys
    let (pk, vk) = client.setup(VERIFY_ELF);
    
    // Generate the proof
    match client.prove(&pk, &stdin).run() {
        Ok(proof) => {
            info!("Successfully generated proof!");
            
            // Verify the proof
            match client.verify(&proof, &vk) {
                Ok(_) => {
                    info!("Successfully verified proof!");
                    
                    // Create the result
                    let result = ProofResult {
                        verification_result: true,
                        proof: hex::encode(&proof),
                        verification_key: hex::encode(&vk),
                        public_values: hex::encode(&proof.public_values),
                    };
                    
                    HttpResponse::Ok().json(result)
                }
                Err(e) => {
                    error!("Failed to verify proof: {}", e);
                    HttpResponse::InternalServerError().json(serde_json::json!({
                        "error": "Failed to verify proof"
                    }))
                }
            }
        }
        Err(e) => {
            error!("Failed to generate proof: {}", e);
            HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Failed to generate proof"
            }))
        }
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Set up more verbose logging
    std::env::set_var("RUST_LOG", "info");
    env_logger::init();
    
    // Try a range of ports if the default is in use
    let ports = [8080, 8081, 8082, 8083, 8084];
    let mut server = None;
    let mut bound_port = None;
    
    for port in ports {
        let bind_address = format!("0.0.0.0:{}", port);
        match HttpServer::new(|| {
            App::new()
                .app_data(web::JsonConfig::default().limit(1024 * 1024 * 10))
                .route("/api/process", web::post().to(process_data))
        })
        .bind(&bind_address) {
            Ok(s) => {
                server = Some(s);
                bound_port = Some(port);
                break;
            }
            Err(e) => {
                error!("Failed to bind to port {}: {}", port, e);
                continue;
            }
        }
    }
    
    match (server, bound_port) {
        (Some(server), Some(port)) => {
            info!("=== Starting GCP Server ===");
            info!("Successfully bound to port {}", port);
            info!("Ready to receive data from Discord bot");
            info!("Press Ctrl+C to stop the server");
            
            server.run().await
        }
        _ => {
            error!("Failed to bind to any available ports");
            std::process::exit(1);
        }
    }
} 