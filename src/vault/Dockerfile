FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Vault CLI for init/unseal
RUN apt-get update && apt-get install -y curl unzip gnupg lsb-release && \
    curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" \
      > /etc/apt/sources.list.d/hashicorp.list && \
    apt-get update && apt-get install -y vault && \
    rm -rf /var/lib/apt/lists/*

COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8080

CMD ["python3", "vault_server.py"]
