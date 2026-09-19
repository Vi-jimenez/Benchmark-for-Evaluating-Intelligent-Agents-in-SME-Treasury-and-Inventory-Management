import json
import os
import time
import anthropic
from config import ANTHROPIC_API_KEY
from tools import HerramientasTesoreria

class AgenteClaude:
    def __init__(self, system_prompt_path="system.txt"):
        with open(system_prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()
            
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-6"
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
            # Gestionar historial manualmente
            messages = []
            
            # Añadir últimos N turnos del historial
            for h in self.history[-self.max_memoria:]:
                messages.append({"role": "user", "content": h['prompt']})
                messages.append({"role": "assistant", "content": h['response']})
            
            # Consigna de rigor y supervivencia
            prompt_actual += "\nATENCIÓN: Lee con extrema atención las normas detalladas en el SYSTEM PROMPT."
            prompt_actual += "\nPRIORIDADES:"
            prompt_actual += "\n1. SOBREVIVIR: Evita la quiebra a toda costa."
            prompt_actual += "\n2. MAXIMIZAR SCORE: Busca el mayor beneficio económico al final."
            prompt_actual += "\nRESPONDE ÚNICAMENTE EN FORMATO JSON."
            
            messages.append({"role": "user", "content": prompt_actual})

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.system_prompt,
                messages=messages,
                temperature=0.0
            )

            text = response.content[0].text
            
            # Limpieza básica por si Claude añade texto fuera del JSON
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                json_text = text[start:end]
                decision = json.loads(json_text)
            else:
                raise ValueError("No se encontró JSON en la respuesta de Claude")

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
            if "429" in str(e) or "overloaded" in str(e):
                print(f"Claude está saturado o Rate Limit. Esperando 10 segundos...", flush=True)
                time.sleep(10)
                return self.ejecutar_turno(tools)
            else:
                print(f"ERROR en Claude: {e}", flush=True)
