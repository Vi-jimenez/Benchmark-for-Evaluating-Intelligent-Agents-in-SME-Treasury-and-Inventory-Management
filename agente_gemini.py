import json
import os
import google.generativeai as genai
import time
from config import GEMINI_API_KEY
from tools import HerramientasTesoreria

class AgenteGemini:
    def __init__(self, system_prompt_path="system.txt"):
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()
            
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Usamos el modelo v2.5 Pro solicitado por el usuario
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-pro",
            generation_config={"temperature": 0.0, "response_mime_type": "application/json"},
            system_instruction=self.system_prompt
        )
        
        self.chat = self.model.start_chat(history=[])
        self.MAX_MEMORIA = 5

    def formatear_estado_para_prompt(self, tools: HerramientasTesoreria):
        estado = tools.obtener_estado()
        pagos = tools.listar_pagos_pendientes()
        
        prompt = f"DÍA {estado['dia']} | CAJA: {estado['caja']}€ | DEUDA: {estado['deuda']} | STOCK: {estado['inventario']}\n"
        prompt += "FACTURAS (paga solo si es crítico o tienes mucha caja):\n"
        for p in pagos[:5]:
            prompt += f"- {p['id']} ({p['importe']}€, {p['dias_hasta_vencimiento']}d, {'CRI' if p['critico'] else 'NOR'})\n"
        
        return prompt

    def ejecutar_turno(self, tools: HerramientasTesoreria):
        dia_actual = tools.obtener_estado()["dia"]
        prompt_actual = self.formatear_estado_para_prompt(tools)
        
        print(f"-> Día {dia_actual} [Gemini 2.5 Pro]: Pensando...", end=" ", flush=True)

        try:
            # Mantener ventana de memoria
            if len(self.chat.history) > (self.MAX_MEMORIA * 2):
                self.chat.history = self.chat.history[-(self.MAX_MEMORIA * 2):]

            response = self.chat.send_message(prompt_actual)
            text = response.text.strip()
            
            # Limpieza y auto-corrección de JSON
            if not text.endswith("}"):
                text += "}}" if not text.endswith("}") else "}"
            
            start = text.find("{")
            end = text.rfind("}") + 1
            decision = json.loads(text[start:end])

            acciones = decision.get("acciones", {})
            
            # Procesar Stock
            pedido = acciones.get("hacer_pedido", {})
            if pedido.get("ejecutar"):
                tools.hacer_pedido(pedido.get("cantidad", 0))

            # Procesar Pagos
            for id_pago in acciones.get("pagar_facturas", []):
                tools.pagar(id_pago)

            # Procesar Crédito
            gestion = acciones.get("gestionar_credito", {})
            if gestion.get("disponer", 0) > 0:
                tools.disponer_credito(gestion.get("disponer"))
            if gestion.get("amortizar", 0) > 0:
                tools.amortizar_credito(gestion.get("amortizar"))

            # Procesar Marketing
            if acciones.get("hacer_marketing"):
                tools.hacer_marketing()

            print(f"OK. Razonamiento: {decision.get('razonamiento', '---')[:40]}...", flush=True)

        except Exception as e:
            if "429" in str(e) or "Quota exceeded" in str(e):
                print("RATE LIMIT detectado. Reintentando en 15 seg...")
                time.sleep(15)
                return self.ejecutar_turno(tools)
            else:
                print(f"ERROR: {e}", flush=True)
                self.chat = self.model.start_chat(history=[])
