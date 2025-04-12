use actix_web::{web, App, HttpResponse, HttpServer, Responder};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use log::{info, error};
use env_logger;
use sp1_sdk::{include_elf, ProverClient, SP1Stdin};
use hex;

// Include the verification program ELF
pub const VERIFY_ELF: &[u8] = include_bytes!("../../verification_proof/elf/riscv32im-succinct-zkvm-elf");

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

#[derive(Debug, Serialize, Deserialize)]
struct PublicValues {
    public_keys: Vec<String>,
    conditions: String,
    signature_verified: bool,
    conditions_verified: bool,
}

async fn process_data(data: web::Json<VerificationData>) -> impl Responder {
    info!("=== GCP Server - Received New Request ===");
    info!("Verification file content:");
    info!("{}", data.verification_file);
    info!("\nJSON dictionaries received:");
    info!("{}", serde_json::to_string_pretty(&data.json_dicts).unwrap());
    
    // Extract signers from json_dicts
    let signers: Vec<String> = data.json_dicts.iter()
        .filter_map(|dict| {
            dict.get("signed_data")
                .and_then(|signed_data| signed_data.as_object())
                .and_then(|signed_data_obj| signed_data_obj.get("signer"))
                .and_then(|signer| signer.as_str())
                .map(String::from)
        })
        .collect();
    
    info!("Extracted signers: {:?}", signers);
    
    // Read and parse public keys file
    let public_keys: HashMap<String, String> = match std::fs::read_to_string("keys/public_keys.json") {
        Ok(content) => serde_json::from_str(&content).unwrap(),
        Err(e) => {
            error!("Failed to read public_keys.json: {}", e);
            return HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Failed to read public keys file"
            }));
        }
    };
    
    // Create vector of just the public keys for our signers
    let relevant_keys: Vec<String> = signers.iter()
        .filter_map(|signer| public_keys.get(signer).cloned())
        .collect();
    
    info!("Found {} relevant public keys", relevant_keys.len());
    
    // Setup the prover client
    let client = ProverClient::from_env();
    
    // Setup the inputs for the proof
    let mut stdin = SP1Stdin::new();
    
    // Write verification conditions
    stdin.write(&data.verification_file);
    
    // Write JSON data
    let json_data = serde_json::to_string(&data.json_dicts).unwrap();
    stdin.write(&json_data);
    
    // Write the vector of public keys
    stdin.write(&relevant_keys);

    // Generate the proving and verification keys
    let (pk, vk) = client.setup(VERIFY_ELF);
    
    // Execute the program and get public values
    let (public_values, report) = client.execute(VERIFY_ELF, &stdin).run().unwrap();
    info!("Executed program with {} cycles", report.total_instruction_count());
    
    // Convert SP1PublicValues to bytes and then deserialize into PublicValues struct
    let public_values_bytes = public_values.to_vec();
    let public_values_struct: PublicValues = match serde_json::from_slice(&public_values_bytes) {
        Ok(values) => {
            info!("Successfully parsed public values: {:?}", values);
            values
        },
        Err(e) => {
            error!("Failed to parse public values: {}", e);
            return HttpResponse::InternalServerError().json(serde_json::json!({
                "error": format!("Failed to parse public values: {}", e)
            }));
        }
    };
    
    // Create the result with public values as a pretty-printed string
    let result = ProofResult {
        verification_result: public_values_struct.signature_verified && public_values_struct.conditions_verified,
        proof: "".to_string(),
        verification_key: "".to_string(),
        public_values: serde_json::to_string_pretty(&public_values_struct).unwrap(),
    };
    
    info!("Sending response with public values: {}", result.public_values);
    HttpResponse::Ok().json(result)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Set up more verbose logging
    std::env::set_var("RUST_LOG", "info");
    env_logger::init();
    
    // Try a range of ports if the default is in use
    let ports = [8080];
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