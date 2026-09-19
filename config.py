# ============================================================
# Parámetros financieros
# ============================================================

# TIN anual de la póliza / línea de crédito
TIN_ANUAL_CREDITO = 0.065

# TIN anual del descubierto tácito
TIN_ANUAL_DESCUBIERTO = 0.29

# Comisión por descubierto sobre el mayor saldo negativo del periodo
COMISION_DESCUBIERTO = 0.055

# Comisión mínima por descubierto en cada liquidación mensual
COMISION_MINIMA_DESCUBIERTO = 20.0

# Límite máximo tolerado de descubierto tácito
LIMITE_DESCUBIERTO = 3000.0

# Interés de demora para pagos no críticos
INTERES_ANUAL_DEMORA = 0.1015

# Horizonte del episodio: 6 meses ~ 180 días
DURACION_EPISODIO = 180

# Liquidación mensual de intereses de la póliza
DIAS_LIQUIDACION_INTERESES_CREDITO = 30

# Liquidación mensual del descubierto tácito
DIAS_LIQUIDACION_DESCUBIERTO = 30

# Probabilidad diaria de gasto variable aleatorio
PROBABILIDAD_GASTO_VARIABLE = 0.05


# ============================================================
# Producto
# ============================================================

NOMBRE_PRODUCTO = "producto_unico"

# Precio de venta por unidad
PRECIO_VENTA_UNIDAD = 800.0

# Coste variable por unidad vendida
COSTE_VARIABLE_UNIDAD_VENDIDA = 50.0

# Coste de almacenaje por unidad y día
COSTE_DIARIO_ALMACENAJE_POR_UNIDAD = 0.33

INVENTARIO_INICIAL = 10


# ============================================================
# Proveedor
# ============================================================

NOMBRE_PROVEEDOR = "proveedor_unico"

# Coste de compra por unidad al proveedor
COSTE_COMPRA_UNIDAD = 400.0

# Coste fijo de emisión por pedido
COSTE_EMISION_PEDIDO = 20.0

# Plazo de entrega del proveedor
DIAS_MINIMOS_ENTREGA = 2
DIAS_MAXIMOS_ENTREGA = 4


# ============================================================
# Demanda
# ============================================================

PROBABILIDAD_DIARIA_VENTA = 0.45
DEMANDA_DIARIA_MINIMA = 1
DEMANDA_DIARIA_MAXIMA = 4


# ============================================================
# Cobro de ventas
# ============================================================

DIAS_MINIMOS_COBRO = 1
DIAS_MAXIMOS_COBRO = 30

# ============================================================
# Marketing
# ============================================================

# Día exacto en el que aparece la oportunidad de marketing
DIA_OPORTUNIDAD_MARKETING = 80

# Coste de la acción de marketing
COSTE_MARKETING = 1500.0

# Incremento sobre la probabilidad diaria de venta
INCREMENTO_PROBABILIDAD_VENTA_MARKETING = 0.10

# Duración del efecto del marketing en días
DURACION_EFECTO_MARKETING = 40

# ============================================================
# API Config
# ============================================================
GEMINI_API_KEY = ""
OPENAI_API_KEY = ""
XAI_API_KEY = ""
ANTHROPIC_API_KEY = ""

