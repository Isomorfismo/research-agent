Enterprise Business Intelligence Research Agent

Agente inteligente especializado en el análisis automatizado de datos empresariales de ventas e inventario. Está desarrollado con Python 3.12+, LangGraph, Ollama y SQLite, y utiliza uv para la gestión de dependencias y del entorno de desarrollo.

El proyecto prioriza la robustez, la validación determinista de datos y la ejecución local mediante modelos de lenguaje. Su objetivo es generar respuestas fundamentadas en datos verificables, reduciendo las alucinaciones y evitando conclusiones que no estén respaldadas por la evidencia disponible.

🏗️ Arquitectura del sistema

El agente utiliza LangGraph para gestionar un flujo de ejecución basado en estados. La arquitectura separa la interpretación flexible del modelo de lenguaje de la ejecución de herramientas y la verificación determinista de los resultados.

Diagrama de flujo
```mermaid
flowchart TD
    START([START]) --> MODEL[model]

    MODEL -->|Hay llamadas a herramientas| EXECUTE[execute_tools]
    MODEL -->|Faltan herramientas obligatorias| RECOVER[recover_missing]
    MODEL -->|Respuesta disponible| END([END])
    MODEL -->|Sin herramientas pendientes| FINALIZE[finalize]

    EXECUTE --> MODEL
    RECOVER -->|Recuperación sin respuesta final| MODEL
    RECOVER -->|Respuesta de error o solicitud de datos| END

    FINALIZE --> END

    style START fill:#d1fae5,stroke:#059669,color:#064e3b
    style END fill:#d1fae5,stroke:#059669,color:#064e3b
    style MODEL fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
    style EXECUTE fill:#fef3c7,stroke:#d97706,color:#78350f
    style RECOVER fill:#fce7f3,stroke:#db2777,color:#831843
    style FINALIZE fill:#ede9fe,stroke:#7c3aed,color:#4c1d95
```

Componentes principales
model: nodo que consulta al modelo de lenguaje, interpreta la pregunta y determina si necesita ejecutar herramientas.
execute_tools: ejecuta las herramientas solicitadas, valida sus argumentos, controla los errores y registra los resultados.
recover_missing: identifica herramientas obligatorias que el modelo no ha solicitado e intenta recuperarlas cuando dispone de la información necesaria.
finalize: prepara la respuesta final cuando no quedan herramientas obligatorias pendientes.
build_verified_answer(): construye respuestas basadas en resultados validados de ventas e inventario, sin inventar cifras ni atribuir causas que no puedan demostrarse.
END: representa la finalización del flujo de ejecución.

El grafo también contempla límites de iteraciones y rutas de salida para evitar ejecuciones indefinidas.

⚙️ Características principales
Respuestas fundamentadas en datos: las cifras de ventas e inventario proceden de las herramientas de consulta y se someten a validación antes de elaborar la respuesta final.
Control de afirmaciones sin evidencia: el agente evita atribuir variaciones de ventas a competidores u otras causas cuando los datos disponibles no permiten demostrarlo.
Validación estricta: comprueba los tipos de datos, los valores numéricos, los campos obligatorios y la coherencia de los resultados.
Ejecución segura de herramientas: contempla nombres de herramientas desconocidos, argumentos malformados y errores internos.
Recuperación de herramientas omitidas: intenta ejecutar las consultas obligatorias que el modelo haya dejado pendientes.
Persistencia local: utiliza SQLite para almacenar y consultar los datos empresariales.
Modelo de lenguaje local: utiliza Ollama para ejecutar modelos en el entorno local.
Pruebas automatizadas: incorpora pruebas para los casos normales, los datos inválidos y las situaciones límite.
La arquitectura está diseñada para reducir las alucinaciones mediante validación y generación determinista de respuestas. Esto no implica que todas las respuestas del modelo estén libres de errores; las afirmaciones deben mantenerse dentro de los límites de la evidencia disponible.
🛠️ Tecnologías utilizadas
Tecnología	Propósito
Python 3.12+	Lenguaje principal
LangGraph	Orquestación del flujo del agente
Ollama	Ejecución local del modelo de lenguaje
SQLite	Almacenamiento y consulta de datos
uv	Gestión del entorno y las dependencias
pytest	Pruebas automatizadas
pytest-cov	Medición de cobertura del código


📋 Requisitos previos

Antes de instalar el proyecto, asegúrate de tener:

Python 3.12 o superior.
uv.
Ollama instalado y disponible localmente.
Git para clonar el repositorio.
🚀 Instalación y configuración
1. Clonar el repositorio

Sustituye la URL de ejemplo por la URL real de tu repositorio:

git clone https://github.com/tu-usuario/research-agent.git
cd research-agent

2. Instalar las dependencias
uv sync


Este comando instala las dependencias declaradas en el proyecto y prepara el entorno administrado por uv.

3. Descargar el modelo de Ollama

Descarga el modelo configurado para el agente:

ollama pull qwen2.5:3b-instruct


Asegúrate de que el nombre del modelo coincida con la configuración utilizada en el código.

4. Inicializar la base de datos

Si el proyecto incluye el script setup_db.py, ejecuta:

uv run python setup_db.py


Este script inicializa la base de datos SQLite y carga los datos sintéticos e históricos definidos por el proyecto.

💻 Uso
Consultar ventas e inventario

Para solicitar un análisis de ventas y consultar el inventario de un producto:

uv run python cli.py ask "Analiza las ventas de PROD-001 de los dos últimos meses y consulta su inventario."

Evaluar una hipótesis sin evidencia suficiente

Para comprobar cómo responde el agente ante una pregunta que atribuye las variaciones a una causa no demostrada:

uv run python cli.py ask "¿La caída de ventas de PROD-001 fue causada por un competidor?"


El agente debe distinguir entre los datos comprobados y las causas que no pueden determinarse con la información disponible.

Consultar directamente las herramientas

Resumen de ventas de los dos últimos meses:

uv run python cli.py sales --product PROD-001 --months 2


Estado del inventario de un producto:

uv run python cli.py inventory --product PROD-002


Los comandos anteriores corresponden a la interfaz descrita por el proyecto. Si cambia la configuración de la CLI, consulta su ayuda con:

uv run python cli.py --help

🧪 Pruebas y evaluación
Ejecutar las pruebas automatizadas

Para ejecutar toda la suite:

uv run pytest -v

Medir la cobertura

Para medir la cobertura de agent.py y database.py:

uv run pytest --cov=database --cov=agent --cov-report=term-missing


La opción term-missing permite identificar las líneas que todavía no están cubiertas por las pruebas.

Estado de las pruebas

En la última ejecución compartida durante el desarrollo se obtuvieron estos resultados:

86 de 86 pruebas superadas.
99 % de cobertura global.
agent.py: 99 % de cobertura.
database.py: 100 % de cobertura.

Estos resultados corresponden a la última ejecución registrada y pueden variar si se modifica el código.

Ejecutar la evaluación de comportamiento

Si evaluate_agent.py está disponible en el repositorio, ejecuta:

uv run python evaluate_agent.py


Esta evaluación está destinada a comprobar el comportamiento del agente ante escenarios definidos y casos límite.

📁 Estructura del proyecto

```mermaid
flowchart TD
    RA[research-agent/] --> agent[agent.py]
    RA --> db[database.py]
    RA --> cli[cli.py]
    RA --> setup[setup_db.py]
    RA --> eval[evaluate_agent.py]
    RA --> cases[evaluation_cases.json]
    RA --> tests[tests/]
    RA --> pyproj[pyproject.toml]
    RA --> lock[uv.lock]
    RA --> readme[README.md]
    RA --> rdb[research.db]

    tests --> t_agent[test_agent.py]
    tests --> t_db[test_database.py]
```



Descripción de los componentes principales:

agent.py: define el estado, los nodos, el grafo de LangGraph, los validadores y la lógica de ejecución del agente.
database.py: contiene las consultas y herramientas para recuperar información de ventas e inventario.
cli.py: proporciona la interfaz de línea de comandos.
setup_db.py: inicializa la base de datos y carga los datos de prueba.
evaluate_agent.py: ejecuta evaluaciones automatizadas del comportamiento del agente.
evaluation_cases.json: contiene los casos de evaluación y sus condiciones esperadas.
tests/: agrupa las pruebas automatizadas.
pyproject.toml: declara las dependencias y la configuración del proyecto.
uv.lock: registra las versiones resueltas de las dependencias.
research.db: base de datos SQLite local, que no debe versionarse si se ha decidido excluirla del repositorio.

La estructura anterior refleja la organización descrita del proyecto. Comprueba que todos los archivos estén presentes antes de utilizarla como inventario definitivo.

🧭 Principios de diseño
Separación de responsabilidades

El modelo de lenguaje interpreta las preguntas y decide qué herramientas necesita. La capa de herramientas recupera los datos y la lógica determinista valida los resultados y construye las respuestas verificadas.

Datos como fuente de verdad

SQLite es la fuente de datos empresariales de la aplicación. El agente no debe sustituir resultados reales por cifras generadas por el modelo.

Validación antes de generar respuestas

Los argumentos y resultados de las herramientas deben cumplir las condiciones de validación antes de utilizarse en la respuesta final.

Manejo controlado de errores

Los errores deben tratarse de manera explícita, evitando que las excepciones internas o los resultados inválidos se conviertan en afirmaciones empresariales.

Desarrollo incremental y verificable

Los cambios se validan mediante pruebas automatizadas para mantener la estabilidad y reducir las regresiones.

🔒 Privacidad y ejecución local

El proyecto está diseñado para utilizar Ollama y SQLite localmente. Esta arquitectura permite mantener el procesamiento en el entorno propio cuando todos los componentes se ejecutan de forma local y no se utilizan servicios externos.

La ejecución completamente offline depende de que el modelo esté descargado previamente, de que las dependencias estén instaladas y de que la configuración no introduzca llamadas externas.

📌 Estado del proyecto

El proyecto dispone de herramientas de consulta de ventas e inventario, validación de datos, orquestación con LangGraph y una suite de pruebas automatizadas.

La siguiente etapa de desarrollo puede centrarse en verificar el flujo completo con Ollama, reforzar las pruebas de integración y documentar los resultados obtenidos en ejecuciones reales.
