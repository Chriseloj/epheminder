<a name="top"></a>
<a name="spanish-version"></a>
# Epheminder – Sistema seguro de recordatorios efímeros

Sistema de recordatorios efímeros seguro  vía línea de comandos (CLI)

Epheminder = Ephemeral + Reminder

Diseñado para crear notas temporales con expiración configurable y limpieza automática.

[Read English version](#english-version)

---

## Tabla de Contenidos
- [Descripción](#descripción)
- [Características](#características)
- [Arquitectura](#arquitectura)
- [Testing](#testing)
- [Variables de entorno críticas](#variables-de-entorno-críticas)
- [Instalación](#instalación)
- [Uso con Docker](#uso-con-docker)
- [Uso / CLI](#uso--cli)
- [Ejemplo de flujo CLI](#ejemplo-de-flujo-cli)
- [Documentation / Slides](#documentación--slides) 

---

## Descripción
`Epheminder` es una aplicación para crear notas digitales efímeras, un sistema seguro de recordatorios que permite tomar notas rápidas de hasta 100 caracteres, con expiración configurable de hasta 7 días.

El proyecto sigue una arquitectura en capas (core / infrastructure) con clara separación de responsabilidades y un enfoque fuerte en seguridad.

Aunque la aplicación se presenta como CLI, la lógica de negocio está desacoplada de la interfaz, lo que permite reemplazar la CLI por una API HTTP sin modificar el dominio.

El objetivo es proporcionar un espacio simple y rápido para notas temporales, evitando la sobrecarga.

---

## Características
🔐 **Autenticación y Seguridad**

- Autenticación con JWT real (PyJWT).
- Access tokens y Refresh tokens con jti único.
- Validación de expiración automática.
- Verificación estricta de tipo de token.
- Política deny-by-default.

- Control de acceso basado en roles (RBAC):
      - SUPERADMIN
      - ADMIN
      - USER
      - GUEST

- Protección contra fuerza bruta:
      - Límite de intentos
      - Bloqueo temporal
      - Backoff exponencial

- Hash de contraseñas con bcrypt.
- Hash de datos sensibles para auditoría (SHA-256 + salt vía .env).

📝 **Gestión de Recordatorios**

- Texto máximo de 100 caracteres.
- Expiración automática hasta 7 días.
- Límite de 23 recordatorios por usuario.
- Eliminación automática mediante scheduler en background.
- Limpieza periódica de refresh tokens expirados.

**Stack Tecnológico**
- **Lenguaje:** Python 3.x
- **Dependencias principales:** python-dotenv, PyJWT, SQLAlchemy, bcrypt
- **Testing:** pytest + pytest-cov
- **Base de datos:** SQLite usando SQLAlchemy
- **Interfaz:** CLI ligera
- **Seguridad:** JWT, RBAC y hashing de contraseñas
---
<a name="arquitectura"></a>
## ⚙ Arquitectura

Epheminder sigue una arquitectura en capas con separación clara de responsabilidades.

La CLI actúa únicamente como interfaz, mientras que la lógica de negocio
permanece desacoplada y reutilizable.

Flujo de capas:

CLI (Interface Layer)
        │
        ▼
Application Flows
        │
        ▼
Core Domain
        │
        ▼
Infrastructure

### Estructura del proyecto

epheminder/
│
├─ app/
│   └─ CLI entrypoint
│  
├─ application/
│   ├─ auth_flow.py
│   ├─ reminder_flow.py
│   └─ session_services.py
│
├─ core/
│   ├─ authentication
│   ├─ authorization (RBAC)
│   ├─ security
│   └─ reminder services
│
├─ infrastructure/
│   ├─ repositories
│   ├─ scheduler
│   └─ storage
│
├─ tests/
│
└─ docs/

##  🧪Testing

- **pytest --cov=.**. Ejecuta todos los tests y genera un reporte de cobertura de código.
- 199 tests automatizados (puede variar por version)
- 94% de cobertura total (puede variar por version)
- Tests unitarios e integración.
- Validación de flujos de autenticación, seguridad y expiración.

⚠ Aviso de Seguridad en Windows

En sistemas POSIX (Linux/macOS), los permisos del archivo de la base de datos se restringen automáticamente al propietario (0600).

En Windows, la aplicación ahora usa ACLs de NTFS para que solo el usuario actual pueda acceder al archivo (equivalente a icacls database.db /inheritance:r /grant:r %USERNAME%:F).
Si se ejecuta en una máquina compartida, asegúrate de que el directorio del proyecto no sea accesible públicamente.

## Variables de entorno críticas

Asegúrate de tener un archivo `.env` en la raíz del proyecto con:

```env
SECRET_KEY=tu_clave_secreta_aqui
JWT_ALGORITHM=HS512
HASH_SALT=tu_salt_aqui
```

## Instalación

1. Clonar el repositorio:
```bash

git clone <URL_DEL_REPOSITORIO>
cd epheminder

```

2. Instalar dependencias:
```bash

pip install -r requirements.txt

```

## 🐳Uso con Docker

También puedes ejecutar Epheminder usando Docker sin instalar Python localmente:

### 1. Construir la imagen:

```bash
docker build -t epheminder:latest .

```

### 2. Crear un contenedor con volumen para la base de datos y variables de entorno:

#### Opción (si tienes docker-compose.yml):
- docker compose run app

## USO / CLI

Ejecutar la aplicación:
```bash

# Opción 1: ejecución normal
python -m app.main

# Opción 2: ejecución con logs en consola y nivel DEBUG
LOG_TO_CONSOLE=true LOG_LEVEL=DEBUG python -m app.main

# Opción 3: ejecución con logs en archivo
LOG_TO_FILE=true python -m app.main

```

## Ejemplo de flujo CLI

```bash
$ python -m app.main
==============================
      Epheminder APP CLI
==============================
1. Register
2. Login
3. Create Reminder
4. List Reminders
5. Delete Reminder
6. Logout
0. Exit

Choose an option: 1
Username: Juan
Password: ****
User 'Juan' registered successfully!

Choose an option: 2
Username: Juan
Password: ****
Login successful.

Choose an option: 3
Reminder text: Nota: el texto del recordatorio puede ser cualquier cosa hasta 100 caracteres.
Expires amount: 1
Expiration unit (m/h/d or minutes/hours/days): days
Reminder created. ID: 1

Choose an option: 4
- ID: 1 | Text: Nota: el texto del recordatorio puede ser cualquier cosa hasta 100 caracteres. | Expires: 2026-03-05 12:00:00

Choose an option: 6
Logged out successfully.

Choose an option: 0
Exiting.
```

## Documentación / Slides

Project slides:

- Version en Español: [Epheminder_Presentation_ES.pdf](./docs/Epheminder_Presentation_ES.pdf)

---
[⬆ Volver arriba](#top) | [English version](#english-version)

---  
<a name="english-version"></a>
## English Version
---

## Epheminder – Secure Ephemeral Reminder CLI

Secure and fast ephemeral reminder system via command-line interface (CLI)

Epheminder = Ephemeral + Reminder

Designed to create temporary notes with configurable expiration and automatic cleanup.

[Leer versión en Español](#spanish-version)

---

## Table of Contents
- [Description](#description)
- [Features](#features)
- [Architecture](#architecture)
- [Testing](#testing)
- [Critical environment variables](#critical-environment-variables)
- [Installation](#installation)
- [Use with Docker](#use-with-docker)
- [Usage / CLI](#usage--cli)
- [CLI Flow Example](#cli-flow-example)
- [Documentation / Slides](#documentation--slides) 

---

## Description
`Epheminder` is an application for creating ephemeral digital notes — a secure reminder system that allows users to take quick notes of up to 100 characters, with configurable expiration up to 7 days.

The project follows a layered architecture (core / infrastructure) with clear separation of concerns and a strong focus on security.

Although presented as a CLI application, the business logic is fully decoupled from the interface, allowing the CLI to be replaced with an HTTP API without changing the core domain.

Its goal is to provide a simple and fast space for temporary notes, avoiding the overload.

---

## Features
🔐 **Authentication & Security**

- Real JWT authentication (PyJWT).
- Access and refresh tokens with unique jti.
- Automatic expiration validation.
- Strict token type verification.
- Deny-by-default authorization policy.

- Role-Based Access Control (RBAC):
      - SUPERADMIN
      - ADMIN
      - USER
      - GUEST

- Brute-force protection:
      - Login attempt limits
      - Temporary lockout
      - Exponential backoff

- Password hashing using bcrypt.
- Sensitive data hashing for audit logs (SHA-256 + environment-based salt).

📝 **Reminder Management**

- Maximum 100 characters per reminder.
- Expiration up to 7 days.
- Maximum 23 reminders per user.
- Automatic cleanup via background scheduler.
- Periodic removal of expired refresh tokens.

**Technology Stack**
- **Language:** Python 3.x
- **Main dependencies:** python-dotenv, PyJWT, SQLAlchemy, bcrypt
- **Testing:** pytest + pytest-cov
- **Database:** SQLite via SQLAlchemy
- **Interface:** Lightweight CLI
- **Security:** JWT, RBAC, and password hashing
---
<a name="architecture"></a>
## ⚙Architecture

Epheminder follows a layered architecture with a clear separation of concerns.

The CLI acts purely as the interface layer, while the business logic
remains fully decoupled and reusable.

Layer flow:

CLI (Interface Layer)
        │
        ▼
Application Flows
        │
        ▼
Core Domain
        │
        ▼
Infrastructure

### Project Structure

epheminder/
│
├─ app/
│   └─ CLI entrypoint
│
├─ application/
│   ├─ auth_flow.py
│   ├─ reminder_flow.py
│   └─ session_services.py
│
├─ core/
│   ├─ authentication
│   ├─ authorization (RBAC)
│   ├─ security
│   └─ reminder services
│
├─ infrastructure/
│   ├─ repositories
│   ├─ scheduler
│   └─ storage
│
├─ tests/
│
└─ docs/

## 🧪Testing

- **pytest --cov=.**. Runs all tests and generates a code coverage report.
- 199 automated tests (may vary per version)
- 94% total coverage (may vary per version)
- Unit and integration tests.
- Security and authentication flows fully tested.

⚠ Windows Security Notice

On POSIX systems (Linux/macOS), the database file permissions are automatically restricted to the owner (0600).

On Windows, the application now uses NTFS ACLs to restrict access to the current user only (equivalent to icacls database.db /inheritance:r /grant:r %USERNAME%:F).
If running on a shared machine, ensure the project directory is not publicly accessible.

## Critical environment variables

Make sure you have a `.env` file in the project root with:

```env
SECRET_KEY=your_secret_key_here
JWT_ALGORITHM=HS512
HASH_SALT=your_salt_here
```

## Installation

1. Clone the repository:
```bash

git clone <REPOSITORY_URL>
cd epheminder

```


2. Install dependencies:
```bash

pip install -r requirements.txt

```

## 🐳Use with Docker

You can also run Epheminder using Docker without installing python locally

### 1. Build image:

```bash
docker build -t epheminder:latest .

```

### 2. Create a container with volume for the database and enviromment variables:

#### Option (if you have a docker-compose.yml file):
- docker compose run app


## Usage / CLI
Run app:
```bash

# Option 1: normal execution
python -m app.main

# Option 2: execution with console logs and debug level
LOG_TO_CONSOLE=true LOG_LEVEL=DEBUG python -m app.main

# Option 3: execution with logs in file
LOG_TO_FILE=true python -m app.main

```

## CLI Flow Example
```bash
$ python -m app.main
==============================
      Epheminder APP CLI
==============================
1. Register
2. Login
3. Create Reminder
4. List Reminders
5. Delete Reminder
6. Logout
0. Exit

Choose an option: 1
Username: Juan
Password: ****
User 'Juan' registered successfully!

Choose an option: 2
Username: Juan
Password: ****
Login successful.

Choose an option: 3
Reminder text: Note: the reminder text can be anything up to 100 characters.
Expires amount: 1
Expiration unit (m/h/d or minutes/hours/days): days
Reminder created. ID: 1

Choose an option: 4
- ID: 1 | Text: Note: the reminder text can be anything up to 100 characters. | Expires: 2026-03-05 12:00:00

Choose an option: 6
Logged out successfully.

Choose an option: 0
Exiting.
```

## Documentation / Slides

Project slides:

- English version: [Epheminder_Presentation_EN.pdf](./docs/Epheminder_Presentation_EN.pdf)

---
[⬆ Back to top](#top) | [Versión en Español](#spanish-version)
