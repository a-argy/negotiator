use actix_web::{web, App, HttpResponse, HttpServer, Responder};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use log::info;
use env_logger;

#[derive(Debug, Serialize, Deserialize)]
struct VerificationData {
    verification_file: String,
    json_dicts: Vec<HashMap<String, serde_json::Value>>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ProofResult {
    received_data: String,
}

async fn process_data(data: web::Json<VerificationData>) -> impl Responder {
    // Log all received data in detail
    info!("=== GCP Server - Received New Request ===");
    info!("Verification file content:");
    info!("{}", data.verification_file);
    info!("\nJSON dictionaries received:");
    info!("{}", serde_json::to_string_pretty(&data.json_dicts).unwrap());
    
    // Send back a simple confirmation response
    let result = ProofResult {
        received_data: "Data received successfully".to_string(),
    };
    
    info!("Sending confirmation response back to client");
    
    HttpResponse::Ok().json(result)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    // Set up more verbose logging
    std::env::set_var("RUST_LOG", "info");
    env_logger::init();
    
    let port = std::env::var("PORT").unwrap_or_else(|_| "8080".to_string());
    let bind_address = format!("0.0.0.0:{}", port);
    
    info!("=== Starting GCP Server ===");
    info!("Listening on: {}", bind_address);
    info!("Ready to receive data from Discord bot");
    info!("Press Ctrl+C to stop the server");
    
    HttpServer::new(|| {
        App::new()
            .app_data(web::JsonConfig::default().limit(1024 * 1024 * 10)) // 10MB limit
            .route("/api/process", web::post().to(process_data))
    })
    .bind(bind_address)?
    .run()
    .await
} 