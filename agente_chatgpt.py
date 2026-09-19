import json
import os
import time
from openai import OpenAI
from config import OPENAI_API_KEY
from tools import HerramientasTesoreria

class AgenteChatGPT:
    def __init__(self, system_prompt_path="system.txt"):
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()
            
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = "gpt-5.4-mini"
        self.max_memoria = 5  # Ventana de 5 días de memoria
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
            # Gestionar historial manualmente (OpenAI no tiene ChatSession automática como Gemini)
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Añadir últimos N turnos del historial
            for h in self.history[-self.max_memoria:]:
                messages.append({"role": "user", "content": h['prompt']})
                messages.append({"role": "assistant", "content": h['response']})
            
            # Consigna de rigor y supervivencia
            prompt_actual += "\nATENCIÓN: Lee con extrema atención las normas detalladas en el SYSTEM PROMPT."
            prompt_actual += "\nPRIORIDADES:"
            prompt_actual += "\n1. SOBREVIVIR: Evita la quiebra a toda costa (objetivo número uno)."
            prompt_actual += "\n2. MAXIMIZAR SCORE AL FINAL DEL DÍA 180: Una vez asegurada la supervivencia, busca el mayor beneficio económico."
            
            messages.append({"role": "user", "content": prompt_actual})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={ "type": "json_object" },
                temperature=0.0
            )

            text = response.choices[0].message.content
            decision = json.loads(text)

            # Guardar en historial
            self.history.append({
                "prompt": prompt_actual,
                "response": text
            })

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
            if "429" in str(e):
                print(f"RATE LIMIT detectado. Esperando 5 segundos...", flush=True)
                time.sleep(5)
                return self.ejecutar_turno(tools) # Reintento recursivo
            else:
                print(f"ERROR: {e}", flush=True)
