import json
import os
import time
from openai import OpenAI
from config import XAI_API_KEY
from tools import HerramientasTesoreria

class AgenteGrok:
    def __init__(self, system_prompt_path="system.txt"):
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()
            
        # La API de xAI es compatible con el SDK de OpenAI
        self.client = OpenAI(
            api_key=XAI_API_KEY,
            base_url="https://api.x.ai/v1"
        )
        # Usamos el modelo旗舰 flagship de razonamiento avanzado de 2026
        self.model = "grok-4.20-reasoning"
        self.max_memoria = 5
        self.history = []

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
        
        print(f"-> Día {dia_actual} [{self.model}]: Pensando...", end=" ", flush=True)

        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            
            for h in self.history[-self.max_memoria:]:
                messages.append({"role": "user", "content": h['prompt']})
                messages.append({"role": "assistant", "content": h['response']})
            
            prompt_actual += "\nIMPORTANTE: Responde ÚNICAMENTE en formato JSON."
            messages.append({"role": "user", "content": prompt_actual})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={ "type": "json_object" },
                temperature=0.0
            )

            text = response.choices[0].message.content
            decision = json.loads(text)

            self.history.append({
                "prompt": prompt_actual,
                "response": text
            })

            acciones = decision.get("acciones", {})
            
            # Pedido
            pedido = acciones.get("hacer_pedido", {})
            if pedido.get("ejecutar"):
                tools.hacer_pedido(pedido.get("cantidad", 0))

            # Pagos
            for id_pago in acciones.get("pagar_facturas", []):
                tools.pagar(id_pago)

            # Crédito
            gestion = acciones.get("gestionar_credito", {})
            if gestion.get("disponer", 0) > 0:
                tools.disponer_credito(gestion.get("disponer"))
            if gestion.get("amortizar", 0) > 0:
                tools.amortizar_credito(gestion.get("amortizar"))

            # Marketing
            if acciones.get("hacer_marketing"):
                tools.hacer_marketing()

            print(f"OK. Razonamiento: {decision.get('razonamiento', '---')[:40]}...", flush=True)

        except Exception as e:
            if "429" in str(e):
                print(f"RATE LIMIT en Grok. Esperando 5 segundos...", flush=True)
                time.sleep(5)
                return self.ejecutar_turno(tools)
            else:
                print(f"ERROR en Grok: {e}", flush=True)
