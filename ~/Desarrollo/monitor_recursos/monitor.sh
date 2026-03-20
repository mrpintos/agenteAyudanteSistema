#!/usr/bin/env bash

# ------------------------------------------------------------------
# monitor.sh – recopila datos de CPU y memoria cada N segundos.
# Los guarda en data.json (formato JSON simple).
# ------------------------------------------------------------------

# Intervalo entre lecturas (en segundos)
INTERVAL=5

# Nombre del archivo de salida
OUTPUT="data.json"

# Función que devuelve la carga de CPU promedio del último segundo
get_cpu() {
    # /proc/stat primera línea: user nice system idle iowait irq softirq steal guest guest_nice
    read -r line < /proc/stat
    set -- $line
    cpu_user=$2; cpu_nice=$3; cpu_system=$4; cpu_idle=$5

    # Suma de todos los campos (para calcular porcentaje)
    total=$((cpu_user+cpu_nice+cpu_system+cpu_idle))
    idle=$cpu_idle

    echo "$total $idle"
}

# Función que devuelve el uso de memoria en % y bytes
get_mem() {
    read -r mem_total mem_free < <(awk '/MemTotal/ {print $2} /MemAvailable/ {print $2}' /proc/meminfo)
    # Convertir a KB -> Bytes
    total_bytes=$((mem_total * 1024))
    free_bytes=$((mem_free * 1024))
    used_bytes=$((total_bytes - free_bytes))
    used_perc=$(awk "BEGIN{printf \"%.1f\", ($used_bytes/$total_bytes)*100}")

    echo "$used_perc $used_bytes"
}

# Inicializamos el JSON con un array vacío
echo '[]' > "$OUTPUT"

while true; do
    # Obtener datos
    read total_cpu idle_cpu < <(get_cpu)
    cpu_used=$(awk "BEGIN{printf \"%.1f\", (1-($idle_cpu/$total_cpu))*100}")

    read mem_perc mem_bytes < <(get_mem)

    timestamp=$(date +%s)  # Unix epoch

    # Creamos un objeto JSON con la lectura actual
    entry="{\"time\":$timestamp,\"cpu\":${cpu_used},\"mem_pct\":${mem_perc},\"mem_bytes\":${mem_bytes}}"

    # Añadimos al array existente en data.json
    tmp=$(mktemp)
    jq ". + [$entry]" "$OUTPUT" > "$tmp" && mv "$tmp" "$OUTPUT"

    sleep $INTERVAL
done
