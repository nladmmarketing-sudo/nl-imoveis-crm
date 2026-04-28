"""
Sistema de alertas via Email.
Envia mensagens pro admin (Anderson) quando algo importante acontece:
- Sessao do Jetimob expirou
- Sync falhou
- Outras notificacoes do sistema

Configuracao em .streamlit/secrets.toml:
    [email]
    smtp_host = "smtp.gmail.com"
    smtp_port = 587
    remetente = "nladmmarketing@gmail.com"
    senha_app = "xxxx xxxx xxxx xxxx"  # App Password do Gmail (NAO a senha normal)
    destinatario = "nladmmarketing@gmail.com"
"""
from __future__ import annotations
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path


def _carrega_secrets() -> dict:
    """Le secrets do Streamlit OU diretamente do TOML quando rodando fora do Streamlit"""
    try:
        import streamlit as st
        return dict(st.secrets)
    except Exception:
        try:
            import tomllib
        except ImportError:
            import toml as tomllib
        path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
        if path.exists():
            try:
                with path.open("rb") as f:
                    return tomllib.load(f)
            except Exception:
                with path.open("r") as f:
                    return tomllib.load(f)
        return {}


def enviar_email(assunto: str, corpo_html: str, destinatario: str | None = None) -> tuple[bool, str]:
    """
    Envia email via SMTP (Gmail por padrao).
    Retorna (sucesso, mensagem_erro).
    """
    secrets = _carrega_secrets()
    cfg = secrets.get("email", {})

    smtp_host = cfg.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(cfg.get("smtp_port", 587))
    remetente = cfg.get("remetente")
    senha = cfg.get("senha_app")
    dest = destinatario or cfg.get("destinatario", remetente)

    if not remetente or not senha:
        return False, "Configuracao de email incompleta em secrets.toml"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = f"NL Imoveis Painel <{remetente}>"
    msg["To"] = dest

    msg.attach(MIMEText(corpo_html, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(remetente, senha)
            server.sendmail(remetente, [dest], msg.as_string())
        return True, "OK"
    except Exception as e:
        return False, str(e)


def alerta_jetimob_expirou() -> tuple[bool, str]:
    """Envia email avisando que sessao do Jetimob expirou"""
    assunto = "🚨 NL Imoveis Painel — Sessao Jetimob Expirou"
    corpo = """
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px;">
        <div style="background: linear-gradient(135deg, #033677, #001833); color: white; padding: 25px; border-radius: 10px 10px 0 0;">
          <h2 style="margin: 0; color: #FFB700;">🚨 Acao Necessaria</h2>
          <p style="margin: 5px 0 0; opacity: 0.9;">Painel NL Imoveis</p>
        </div>
        <div style="background: white; padding: 25px; border: 1px solid #E5E7EB; border-top: none; border-radius: 0 0 10px 10px;">
          <h3 style="color: #033677;">Sessao do Jetimob expirou</h3>
          <p>O sync automatico de vendas <strong>parou de funcionar</strong> porque a sessao do Jetimob expirou.</p>

          <p><strong>O que fazer:</strong></p>
          <ol>
            <li>Abra o Terminal no seu Mac</li>
            <li>Cole esses 2 comandos:</li>
          </ol>

          <pre style="background: #F3F6FA; padding: 15px; border-radius: 8px; font-size: 13px; overflow-x: auto;">
cd "~/Documents/Claude/Projects/Gerente de marketing NL imóveis/nl-imoveis-crm"
.venv/bin/python scripts/login_jetimob.py</pre>

          <ol start="3">
            <li>Vai abrir o Chrome — faca login no Jetimob normalmente</li>
            <li>O script fecha sozinho quando detectar o login</li>
            <li>Pronto! O sync volta a funcionar nas proximas execucoes (6h, 12h, 18h, 23h)</li>
          </ol>

          <p style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #E5E7EB; font-size: 12px; color: #6B7280;">
            Esta e uma notificacao automatica do sistema · NL Imoveis · CRECI 1440 J
          </p>
        </div>
      </body>
    </html>
    """
    return enviar_email(assunto, corpo)


def alerta_generico(titulo: str, mensagem: str) -> tuple[bool, str]:
    """Envia alerta generico via email"""
    assunto = f"NL Imoveis Painel — {titulo}"
    corpo = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px;">
        <div style="background: linear-gradient(135deg, #033677, #001833); color: white; padding: 25px; border-radius: 10px 10px 0 0;">
          <h2 style="margin: 0; color: #FFB700;">🔔 {titulo}</h2>
          <p style="margin: 5px 0 0; opacity: 0.9;">Painel NL Imoveis</p>
        </div>
        <div style="background: white; padding: 25px; border: 1px solid #E5E7EB; border-top: none; border-radius: 0 0 10px 10px;">
          <p style="font-size: 15px; line-height: 1.6;">{mensagem}</p>
          <p style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #E5E7EB; font-size: 12px; color: #6B7280;">
            Notificacao automatica do sistema · NL Imoveis
          </p>
        </div>
      </body>
    </html>
    """
    return enviar_email(assunto, corpo)
