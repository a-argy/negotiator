FROM rust:1.75-slim as builder

WORKDIR /usr/src/app
COPY . .

RUN apt-get update && \
    apt-get install -y pkg-config libssl-dev && \
    cargo build --release

FROM debian:bullseye-slim

WORKDIR /usr/src/app
COPY --from=builder /usr/src/app/target/release/gcp-script .

EXPOSE 8080

CMD ["./gcp-script"] 