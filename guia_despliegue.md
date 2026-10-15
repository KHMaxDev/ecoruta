# Guía de Despliegue de EcoRuta

Guía paso a paso para **inicializar el proyecto, levantar el backend y ver la
aplicación en tu navegador**.

> **Resultado final:** abre `http://localhost:5173` y verás el planificador de
> rutas (mapa + frente de Pareto + comparativa). La API queda en
> `http://localhost:8010` y su documentación interactiva en
> `http://localhost:8010/docs`.

---

## Resumen rápido (TL;DR)

Desde la raíz del repositorio, en **Git Bash**:

```bash
# 1. Crear el archivo de entorno
cp .env.example .env

# 2. Levantar PostgreSQL+PostGIS y Redis
docker compose up -d postgis redis

# 3. Cargar los perfiles de vehículo (la carpeta seeds NO se auto-ejecuta)
docker exec -i ecoruta_postgis psql -U ecoruta_user -d ecoruta_db < database/seeds/010_vehicle_profiles.sql

# 4. Construir y levantar el backend (compila el núcleo Rust)
docker compose --profile full up -d --build backend

# 5. Levantar el frontend
cd frontend
npm install
npm run dev
```

Luego abre **http://localhost:5173**.

---

## 1. Requisitos previos

| Herramienta | Versión mínima | Verificar con | Notas |
|---|---|---|---|
| **Docker Desktop** | 24+ (con Compose v2) | `docker --version` | Debe estar **iniciado** (ícono verde). |
| **Node.js** | 20 LTS o 22 | `node --version` | Incluye `npm`. |
| **Git** | 2.40+ | `git --version` | Para clonar. |
| Navegador | Chrome/Edge/Firefox | — | WebGL habilitado (para el mapa). |

**No necesitas** Rust ni Python en tu máquina: el núcleo Rust (`rust_core`) se
compila **dentro** de Docker al construir el backend.

> **Puerto 8000:** el proyecto usa el **8010** a propósito (el 8000 suele estar
> ocupado por `php artisan serve` / XAMPP).

---

## 2. Clonar el repositorio

```bash
git clone https://github.com/KHMaxDev/ecoruta.git
cd ecoruta
```

(Todos los comandos siguientes se ejecutan **desde la raíz** del repositorio,
salvo los del frontend, que indican `cd frontend`.)

---

## 3. Crear el archivo de entorno `.env`

El repositorio **no incluye** `.env` (está en `.gitignore`). Cópialo del ejemplo:

**Git Bash / macOS / Linux**
```bash
cp .env.example .env
```

**Windows PowerShell**
```powershell
Copy-Item .env.example .env
```

Los valores por defecto ya funcionan para uso local. Lo esencial:

```dotenv
POSTGRES_USER=ecoruta_user
POSTGRES_PASSWORD=ecoruta_secure_password
POSTGRES_DB=ecoruta_db
API_PORT=8010
VITE_API_BASE_URL=http://localhost:8010
```

> Si cambias `POSTGRES_USER/PASSWORD/DB`, usa los mismos valores en el paso 5.

---

## 4. Levantar la infraestructura (PostgreSQL + PostGIS + Redis)

```bash
docker compose up -d postgis redis
```

La **primera vez**, PostgreSQL ejecuta automáticamente `database/init_db.sql`
(crea tablas, índices GIST, extensiones PostGIS/pgRouting).

Comprueba que ambos estén **saludables**:

```bash
docker compose ps
```

Debes ver `ecoruta_postgis` y `ecoruta_redis` con estado `healthy`.

> **Valhalla local:** el servicio `valhalla` del compose descarga ~650 MB de OSM
> y consume 8–12 GB de RAM. **No lo necesitas**: el motor de rutas usa los
> servicios públicos de OSRM/Valhalla por internet. Omítelo salvo que quieras
> tiles locales.

---

## 5. Cargar los datos semilla

### 5.1 Perfiles de vehículo (obligatorio)

La carpeta `database/seeds/` está montada como subdirectorio y el entrypoint de
Postgres **no** ejecuta archivos en subcarpetas. Cárgala manualmente (es
idempotente):

**Git Bash**
```bash
docker exec -i ecoruta_postgis psql -U ecoruta_user -d ecoruta_db < database/seeds/010_vehicle_profiles.sql
```

**Windows PowerShell**
```powershell
Get-Content database/seeds/010_vehicle_profiles.sql | docker exec -i ecoruta_postgis psql -U ecoruta_user -d ecoruta_db
```

Verifica (debe devolver `5`):

```bash
docker exec ecoruta_postgis psql -U ecoruta_user -d ecoruta_db -t -c "SELECT COUNT(*) FROM vehicle_profiles;"
```

### 5.2 Red vial de demostración (opcional pero recomendado)

Si no tienes aún los shapefiles del INEGI, carga una red sintética para tener
rutas navegables de inmediato:

**Opción A — malla rápida por SQL**

```bash
# Git Bash
docker exec -i ecoruta_postgis psql -U ecoruta_user -d ecoruta_db < scripts/seed_demo_network.sql
```

**Opción B — corredor CDMX–Toluca–Puebla con pendientes (requiere backend construido)**

```bash
docker cp scripts/seed_demo_corridor.py ecoruta_backend:/tmp/seed_corridor.py
docker exec -e DB_HOST=postgis -e DB_NAME=ecoruta_db -e DB_USER=ecoruta_user -e DB_PASSWORD=ecoruta_secure_password ecoruta_backend python /tmp/seed_corridor.py
```

---

## 6. Construir y levantar el backend (FastAPI + Rust)

```bash
docker compose --profile full up -d --build backend
```

Esto hace 3 cosas dentro de Docker: compila `rust_core` (maturin → wheel),
instala las dependencias Python y arranca Uvicorn. **La primera compilación
tarda unos minutos.**

Verifica que responde:

```bash
curl http://localhost:8010/health
# {"status":"ok","service":"EcoRuta API"}
```

Documentación interactiva de la API: **http://localhost:8010/docs**

Endpoints principales (prefijo `/api/v1`):

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/v1/routes/optimize` | Frente de Pareto punto a punto |
| `POST` | `/api/v1/routes/optimize-multistop` | Ruta con paradas múltiples |
| `GET`  | `/api/v1/vehicles/profiles` | Perfiles de vehículo |
| `GET`  | `/api/v1/weather` | Clima en la ruta |
| `GET`  | `/health` | Healthcheck |

---

## 7. Levantar el frontend (React + Vite)

En otra terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite muestra algo como:

```
  VITE v6.x  ready in 500 ms
  ➜  Local:   http://localhost:5173/
```

El frontend hace *proxy* de `/api` hacia `http://localhost:8010` (configurado en
`frontend/vite.config.ts`), así que **no hay problemas de CORS**.

---

## 8. Ver la aplicación en el navegador

Abre **http://localhost:5173**.

1. En el panel de configuración elige **Origen** y **Destino** (ciudades
   predefinidas; p. ej. CDMX → Puebla) y la hora de salida.
2. Selecciona el **perfil de vehículo**.
3. Pulsa **Calcular**.
4. Verás en el mapa la(s) ruta(s) real(es), la tabla comparativa
   (EcoRuta vs. OSRM vs. Valhalla + enlace a Google Maps) y las gráficas del
   frente de Pareto (costo vs. tiempo).

> La primera consulta puede tardar unos segundos (consulta a servicios públicos
> de enrutamiento + precios de combustible).

---

## 9. Flujo completo (un solo bloque, Git Bash)

```bash
cp .env.example .env
docker compose up -d postgis redis
docker exec -i ecoruta_postgis psql -U ecoruta_user -d ecoruta_db < database/seeds/010_vehicle_profiles.sql
docker exec -i ecoruta_postgis psql -U ecoruta_user -d ecoruta_db < scripts/seed_demo_network.sql
docker compose --profile full up -d --build backend
cd frontend && npm install && npm run dev
```

---

## 10. Comandos de operación

**Estado y logs**
```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f postgis
```

**Reiniciar el backend tras un cambio en `backend/`**
```bash
docker compose --profile full up -d --build backend
docker exec ecoruta_redis redis-cli FLUSHALL   # limpia la caché de rutas
```

**Detener todo (conserva los datos)**
```bash
docker compose --profile full down
```

**Borrar TODO, incluidos los datos de la base (vuelve a ejecutar `init_db.sql`)**
```bash
docker compose --profile full down -v
```

**Reset solo de la base de datos**
```bash
docker compose down -v postgis
docker compose up -d postgis
```

**Frontend: build de producción y previsualización**
```bash
cd frontend
npm run build     # type-check estricto + bundle en frontend/dist
npm run preview   # sirve el build en http://localhost:4173
```

---

## 11. Solución de problemas

| Síntoma | Causa / Solución |
|---|---|
| `failed to connect to the docker API ... dockerDesktopLinuxEngine` | Docker Desktop no está iniciado. Ábrelo y espera a que el motor arranque. |
| El backend no arranca / `port is already allocated` en 8000 | El proyecto usa **8010**. Verifica `API_PORT=8010` en `.env` y que el 8010 esté libre. |
| `/api/v1/vehicles/profiles` devuelve `[]` | No cargaste `database/seeds/010_vehicle_profiles.sql` (paso 5.1). |
| Rutas `0` / errores 502 en `optimize` | Los servicios públicos de OSRM/Valhalla están saturados o sin internet. Reintenta; el backend hace *fallback* entre proveedores. |
| Error de CORS o `/api` 404 en el navegador | El backend no está en el 8010, o el frontend no se sirve desde el 5173. Revisa `VITE_API_TARGET` / `frontend/vite.config.ts` y `.env`. |
| Cambié columnas de la base y no se aplican | `init_db.sql` solo corre al crear el volumen. Recrea: `docker compose down -v postgis` y vuelve a `.up`. |
| El frontend no refleja cambios | Ya usa *Fast Refresh* de Vite; si no, reinicia `npm run dev`. Si hay caché, borra `frontend/node_modules/.vite`. |
| `npm install` falla | Usa Node 20/22 LTS y borra `node_modules` + `package-lock.json` antes de reintentar. |

---

## 12. Arquitectura de puertos

| Servicio | Puerto local | Contenedor | Notas |
|---|---|---|---|
| Frontend (Vite dev) | **5173** | — | Abre esta URL en el navegador |
| Backend (FastAPI) | **8010** | 8000 | `API_PORT` en `.env` |
| PostgreSQL + PostGIS | 5432 | 5432 | Datos en volumen `pgdata` |
| Redis | 6379 | 6379 | Caché de rutas |
| Valhalla local (opcional) | 8002 | 8002 | Solo si levantas el servicio `valhalla` |

---

## 13. Verificación del núcleo Rust (opcional, desarrolladores)

Para validar el motor multiobjetivo (debe dar 7/7) sin necesidad de MSVC en
Windows, usa Docker:

```bash
docker run --rm -v "$PWD/rust_core:/app" -w /app rust:1.99 cargo test --release --no-default-features
```

Esperado:

```
test result: ok. 7 passed; 0 failed
```
