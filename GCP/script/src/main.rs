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

async fn process_data(data: web::Json<VerificationData>) -> impl Responder {
    info!("=== GCP Server - Received New Request ===");
    info!("Verification file content:");
    info!("{}", data.verification_file);
    info!("\nJSON dictionaries received:");
    info!("{}", serde_json::to_string_pretty(&data.json_dicts).unwrap());
    
    // Extract signers from json_dicts
    let signers: Vec<String> = data.json_dicts.iter()
        .filter_map(|dict| {
            dict.get("signer")
                .and_then(|signer| signer.as_str())
                .map(|s| s.to_string())
        })
        .collect();
    
    // Read public keys from file
    let all_public_keys: HashMap<String, String> = match std::fs::read_to_string("../../keys/public_keys.json") {
        Ok(keys) => serde_json::from_str(&keys).unwrap(),
        Err(e) => {
            error!("Failed to read public keys: {}", e);
            return HttpResponse::InternalServerError().json(serde_json::json!({
                "error": "Failed to read public keys"
            }));
        }
    };
    
    // Filter public keys to only include those of the signers
    let relevant_public_keys: HashMap<String, String> = signers.into_iter()
        .filter_map(|signer| {
            all_public_keys.get(&signer)
                .map(|key| (signer, key.clone()))
        })
        .collect();
    
    // Setup the prover client
    let client = ProverClient::from_env();
    
    // Setup the inputs for the proof
    let mut stdin = SP1Stdin::new();
    
    // Write verification conditions
    stdin.write(&data.verification_file);
    
    // Write JSON data
    let json_data = serde_json::to_string(&data.json_dicts).unwrap();
    stdin.write(&json_data);
    
    // Write relevant public keys
    let public_keys_json = serde_json::to_string(&relevant_public_keys).unwrap();
    stdin.write(&public_keys_json);


    // Generate the proving and verification keys
    let (pk, vk) = client.setup(VERIFY_ELF);
    
    // Execute the program and get public values
    let (public_values, report) = client.execute(VERIFY_ELF, &stdin).run().unwrap();
    info!("Executed program with {} cycles", report.total_instruction_count());
    
    // Decode the public values back into the PublicValues struct
    let public_values_struct: PublicValues = serde_json::from_slice(&public_values).unwrap();
    
    // Create the result with public values
    let result = ProofResult {
        verification_result: true,
        proof: "".to_string(),  // Not needed for now
        verification_key: "".to_string(),  // Not needed for now
        public_values: serde_json::to_string_pretty(&public_values_struct).unwrap(),
    };
    
    HttpResponse::Ok().json(result)
        
        // // Generate the proof
        // match client.prove(&pk, &stdin).run() {
        //     Ok(proof) => {
        //         info!("Successfully generated proof!");
                
        //         // Verify the proof
        //         match client.verify(&proof, &vk) {
        //             Ok(_) => {
        //                 info!("Successfully verified proof!");
                        
        //                 // Create the result
        //                 let result = ProofResult {
        //                     verification_result: true,
        //                     proof: hex::encode(&proof),
        //                     verification_key: hex::encode(&vk),
        //                     public_values: hex::encode(&proof.public_values),
        //                 };
                        
        //                 HttpResponse::Ok().json(result)
        //             }
        //             Err(e) => {
        //                 error!("Failed to verify proof: {}", e);
        //                 HttpResponse::InternalServerError().json(serde_json::json!({
        //                     "error": "Failed to verify proof"
        //                 }))
        //             }
        //         }
        //     }
        //     Err(e) => {
        //         error!("Failed to generate proof: {}", e);
        //         HttpResponse::InternalServerError().json(serde_json::json!({
        //             "error": "Failed to generate proof"
        //         }))
        //     }
        // }
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