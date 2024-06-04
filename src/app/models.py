from sqlalchemy import Column, String, DateTime, Date, Integer, ForeignKey, JSON, CheckConstraint, func
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome_completo = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    senha = Column(String, nullable=False)
    data_nascimento = Column(Date, nullable=False)
    sexo_biologico = Column(String(1), CheckConstraint("sexo_biologico IN ('M', 'F')"), nullable=False)
    data_criacao = Column(DateTime, default=func.now())
    formulario = Column(JSON)
    status_formulario = Column(String(20), CheckConstraint("status_formulario IN ('Preenchido', 'Em andamento', 'Não iniciado')"), default='Não iniciado')

class Exame(Base):
    __tablename__ = "exames"

    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey('usuarios.id'))
    nome_exame = Column(String, index=True)
    url = Column(String)
    data_submissao = Column(DateTime, default=datetime.utcnow)
    usuario = relationship("Usuario", back_populates="exames")

Usuario.exames = relationship("Exame", order_by=Exame.id, back_populates="usuario")