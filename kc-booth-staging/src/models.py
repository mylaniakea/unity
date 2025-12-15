from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from .database import Base

class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String, unique=True, index=True)
    ip_address = Column(String, unique=True, index=True)
    username = Column(String)
    password = Column(String)  # Encrypted with Fernet
    ssh_key_id = Column(Integer, ForeignKey("ssh_keys.id"))

class SSHKey(Base):
    __tablename__ = "ssh_keys"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    public_key = Column(String, unique=True)
    private_key = Column(String)  # Encrypted with Fernet

class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    certificate = Column(String, unique=True)
    key = Column(String, unique=True)
    expires_at = Column(DateTime)
    server_id = Column(Integer, ForeignKey("servers.id"))
