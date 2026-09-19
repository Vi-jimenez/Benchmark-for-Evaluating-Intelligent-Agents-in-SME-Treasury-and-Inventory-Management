from runner import ejecutar_episodio
from agente_chatgpt import AgenteChatGPT
import json
import sys

def simular_chatgpt_completo():
    print("Iniciando simulación completa con ChatGPT (180 días)...", flush=True)
    
    agente = AgenteChatGPT()
    try:
        # Ejecutamos el episodio completo (Semilla 0, Límite 15000)
        resultado = ejecutar_episodio(agente.ejecutar_turno, semilla=0, limite_credito=15000)
        
        # Guardamos el resultado en un archivo
        with open("resultado_chatgpt.json", "w") as f:
            json.dump(resultado, f, indent=4)
            
        print("\n--- SIMULACIÓN FINALIZADA ---", flush=True)
        print(f"Día final: {resultado['dia_final']}", flush=True)
        print(f"Estado: {'VIVA' if not resultado['en_quiebra'] else 'QUIEBRA'}", flush=True)
        print(f"Score Final: {resultado['score']}", flush=True)
        print(f"Caja Final: {resultado['caja_final']}€", flush=True)
        
        print("\n--- DESGLOSE DEL SCORE FINAL ---", flush=True)
        for concepto, valor in resultado["detalle_score"].items():
            print(f"- {concepto.replace('_', ' ').capitalize()}: {valor:,.2f}€", flush=True)

    except Exception as e:
        print(f"Error fatal en la simulación: {e}", flush=True)

if __name__ == "__main__":
    simular_chatgpt_completo()
