# Epheminder 📝 – Sistema seguro de recordatorios efímeros

Sistema de recordatorios efímeros seguro y rápido vía línea de comandos (CLI)

Epheminder = Ephemeral + Reminder

Ideal para notas temporales que se eliminan automáticamente, sin necesidad de gestionarlas manualmente.

**English version below / Versión en inglés abajo**

---

## Tabla de Contenidos
- [Descripción](#descripción)
- [Características](#características)
- [Arquitectura](#arquitectura)
- [Testing](#testing)
- [Variables de entorno críticas](#variables-de-entorno-críticas)
- [Instalación](#instalación)
- [Uso / CLI](#uso--cli)
- [Ejemplo de flujo CLI](#ejemplo-de-flujo-cli)
- [Documentation / Slides](#documentación--slides) 

---

## Descripción
`Epheminder` es una aplicación para crear post-its digitales efímeros, un sistema seguro de recordatorios que permite tomar notas rápidas de hasta 100 caracteres, con expiración automática de hasta 7 días.

El proyecto sigue una arquitectura en capas (core / infrastructure) con clara separación de responsabilidades y un enfoque fuerte en seguridad.

Aunque la aplicación se presenta como CLI, la lógica de negocio está desacoplada de la interfaz, lo que permite reemplazar la CLI por una API HTTP sin modificar el dominio.

El objetivo es proporcionar un espacio simple y rápido para notas temporales, evitando la sobrecarga de otras apps de notas o tareas.

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

## ⚙Arquitectura

Epheminder sigue una arquitectura en capas:

core/
 ├─ autenticación
 ├─ autorización (RBAC)
 ├─ servicios de dominio
 ├─ seguridad
 └─ lógica de negocio

infrastructure/
 ├─ repositorios
 ├─ almacenamiento (SQLAlchemy)
 └─ schedulers (daemon threads)

La CLI actúa como interfaz, mientras que la lógica de negocio
permanece desacoplada y reutilizable.

##  🧪Testing

- **pytest --cov=.**. Ejecuta todos los tests y genera un reporte de cobertura de código.
- 178 tests automatizados.
- 93% de cobertura total.
- Tests unitarios e integración.
- Validación de flujos de autenticación, seguridad y expiración.

⚠ **Nota sobre Windows y variables de entorno**

En sistemas Windows, los permisos del archivo de la base de datos (`database.db`) no se restringen automáticamente como en sistemas POSIX. Si varios usuarios comparten la máquina, asegúrate de proteger este archivo.  

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

## USO/CLI

3. Ejecutar la aplicación:
```bash

python -m app.main

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
Expires in amount: 1
Unit (minutes/hours/days): days
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
## English Version
---

# Epheminder 📝 – Secure Ephemeral Reminder CLI

Secure and fast ephemeral reminder system via command-line interface (CLI)

Epheminder = Ephemeral + Reminder

Perfect for temporary notes that self-destruct automatically, without manual cleanup.

---

## Table of Contents
- [Description](#description)
- [Features](#features)
- [Architecture](#architecture)
- [Testing](#testing)
- [Critical environment variables](#critical-environment-variables)
- [Installation](#installation)
- [Usage / CLI](#usage--cli)
- [CLI Flow Example](#cli-flow-example)
- [Documentation / Slides](#documentation--slides) 

---

## Description
`Epheminder` is an application to create ephemeral digital post-its, a secure reminder system that allows users to take quick notes of up to 100 characters, automatically expiring within 7 days.

The project follows a layered architecture (core / infrastructure) with clear separation of concerns and a strong focus on security.

Although presented as a CLI application, the business logic is fully decoupled from the interface, allowing the CLI to be replaced with an HTTP API without changing the core domain.

Its goal is to provide a simple and fast space for temporary notes, avoiding the overload of other note-taking or task apps.

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
## ⚙Architecture

Epheminder follows a layered architecture:

core/
 ├─ authentication
 ├─ authorization (RBAC)
 ├─ domain services
 ├─ security
 └─ business logic

infrastructure/
 ├─ repositories
 ├─ storage (SQLAlchemy)
 └─ schedulers (daemon threads)

The CLI acts as the interface, while the business logic
remains fully decoupled and reusable.

## 🧪Testing

- **pytest --cov=.**. Runs all tests and generates a code coverage report.
- 178 automated tests.
- 93% total coverage.
- Unit and integration tests.
- Security and authentication flows fully tested.

⚠ **Windows and Environment Variables Notice**

On Windows systems, the database file (database.db) permissions are not automatically restricted as on POSIX systems. If multiple users share the machine, make sure to secure this file.

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

## Usage/CLI
3. Run app:
```bash

python -m app.main

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
Expires in amount: 1
Unit (minutes/hours/days): days
Reminder created. ID: 1

Choose an option: 4
- ID: 1 | Text: Note: the reminder text can be anything up to 100 characters.| Expires: 2026-03-05 12:00:00

Choose an option: 6
Logged out successfully.

Choose an option: 0
Exiting.
```

## Documentation / Slides

Project slides:

- English version: [Epheminder_Presentation_EN.pdf](./docs/Epheminder_Presentation_EN.pdf)
