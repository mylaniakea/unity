from sqlalchemy.orm import Session
from . import models, schemas, encryption

# SSH Keys

def get_ssh_key(db: Session, ssh_key_id: int):
    db_ssh_key = db.query(models.SSHKey).filter(models.SSHKey.id == ssh_key_id).first()
    if db_ssh_key:
        # Decrypt private key when retrieving
        db_ssh_key.private_key = encryption.decrypt(db_ssh_key.private_key)
    return db_ssh_key

def get_ssh_key_by_name(db: Session, name: str):
    db_ssh_key = db.query(models.SSHKey).filter(models.SSHKey.name == name).first()
    if db_ssh_key:
        # Decrypt private key when retrieving
        db_ssh_key.private_key = encryption.decrypt(db_ssh_key.private_key)
    return db_ssh_key

def get_ssh_keys(db: Session, skip: int = 0, limit: int = 100):
    ssh_keys = db.query(models.SSHKey).offset(skip).limit(limit).all()
    # Decrypt private keys when retrieving
    for key in ssh_keys:
        key.private_key = encryption.decrypt(key.private_key)
    return ssh_keys

def create_ssh_key(db: Session, ssh_key: schemas.SSHKeyCreate):
    # Encrypt private key before storing
    encrypted_private_key = encryption.encrypt(ssh_key.private_key)
    
    db_ssh_key = models.SSHKey(
        name=ssh_key.name,
        public_key=ssh_key.public_key,
        private_key=encrypted_private_key,
    )
    db.add(db_ssh_key)
    db.commit()
    db.refresh(db_ssh_key)
    
    # Decrypt for return (though it won't be in API response due to schema)
    db_ssh_key.private_key = ssh_key.private_key
    return db_ssh_key

# Servers

def get_server(db: Session, server_id: int):
    db_server = db.query(models.Server).filter(models.Server.id == server_id).first()
    if db_server and db_server.password:
        # Decrypt password when retrieving
        db_server.password = encryption.decrypt(db_server.password)
    return db_server

def get_server_by_hostname(db: Session, hostname: str):
    db_server = db.query(models.Server).filter(models.Server.hostname == hostname).first()
    if db_server and db_server.password:
        # Decrypt password when retrieving
        db_server.password = encryption.decrypt(db_server.password)
    return db_server

def get_servers(db: Session, skip: int = 0, limit: int = 100):
    servers = db.query(models.Server).offset(skip).limit(limit).all()
    # Decrypt passwords when retrieving
    for server in servers:
        if server.password:
            server.password = encryption.decrypt(server.password)
    return servers

def create_server(db: Session, server: schemas.ServerCreate):
    # Encrypt password before storing
    encrypted_password = encryption.encrypt(server.password)
    
    db_server = models.Server(
        hostname=server.hostname,
        ip_address=server.ip_address,
        username=server.username,
        password=encrypted_password,
        ssh_key_id=server.ssh_key_id,
    )
    db.add(db_server)
    db.commit()
    db.refresh(db_server)
    
    # Decrypt for return (though it won't be in API response due to schema)
    db_server.password = server.password
    return db_server

# Certificates

def get_certificate(db: Session, certificate_id: int):
    return db.query(models.Certificate).filter(models.Certificate.id == certificate_id).first()

def get_certificates(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Certificate).offset(skip).limit(limit).all()

def create_certificate(db: Session, certificate: schemas.CertificateCreate):
    db_certificate = models.Certificate(**certificate.dict())
    db.add(db_certificate)
    db.commit()
    db.refresh(db_certificate)
    return db_certificate
