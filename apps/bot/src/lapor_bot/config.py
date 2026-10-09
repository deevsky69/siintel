"""Konfigurasi bot — seluruhnya dari lingkungan; tidak ada nilai rahasia di kode."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    #: Alamat API PREDIKSI PRESISI, tanpa akhiran /api/v1.
    api_base: str = "http://api:8000"
    #: Kunci bersama untuk /messaging/* — harus sama dengan MESSAGING_API_KEY pada API.
    messaging_api_key: str = ""

    #: Token dari @BotFather. Kosong = kanal Telegram tidak dijalankan.
    telegram_bot_token: str = ""
    #: Jeda pemeriksaan kabar perkembangan, detik.
    notify_interval_seconds: int = 30

    #: WhatsApp Business Platform (Meta Cloud API). Ketiganya kosong = kanal tidak dijalankan.
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    #: App secret aplikasi Meta — untuk memverifikasi tanda tangan X-Hub-Signature-256 setiap
    #: webhook. Tanpa ini siapa pun dapat mengirim POST palsu atas nama nomor mana pun.
    whatsapp_app_secret: str = ""
    #: Twilio (Sandbox for WhatsApp untuk peragaan, atau nomor resmi lewat Twilio).
    #: Kanal berjalan bila SID, auth token, nomor pengirim, dan URL webhook publik terisi.
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    #: mis. whatsapp:+14155238886 (nomor sandbox) — lihat Twilio Console.
    twilio_whatsapp_from: str = ""
    #: URL webhook persis seperti yang didaftarkan di Twilio, dipakai memverifikasi tanda
    #: tangan: https://<domain>/webhook/twilio
    twilio_webhook_url: str = ""

    #: Port penerima webhook (WhatsApp Cloud API dan Twilio berbagi satu server).
    webhook_port: int = 8080

    log_level: str = "info"
