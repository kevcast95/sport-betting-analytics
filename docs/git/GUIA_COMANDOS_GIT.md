# Guía rápida de Git (equipo local ↔ remoto)

Sirve para **subir cambios sin depender del asistente** y para entender **por qué “no se subió todo”**.

---

## Por qué a veces solo se suben “algunos” archivos

### 1. Solo agregaste parte del árbol

Git solo incluye lo que vos **explicitamente** ponés en el *staging area*:

| Comando | Qué entra |
|--------|-----------|
| `git add archivo.ts` | Solo ese archivo |
| `git add apps/api/` | Solo esa carpeta |
| `git add -A` (o `git add --all`) | **Todo** lo modificado/eliminado **y** archivos nuevos **respetando `.gitignore`** |
| `git add .` | Todo bajo el directorio actual (ojo: no incluye cambios fuera si estás en un subdirectorio) |

Si en tu consola hiciste `git add` sobre **unos paths concretos**, el commit solo lleva eso. **`git status`** antes del commit muestra qué está en verde (*staged*) y qué sigue en rojo (*no staged*).

### 2. `.gitignore` los excluye (no son “olvido”; Git los ignora)

En este repo, entre otros, **no se versionan** por diseño:

- `.env`, `apps/web/.env*` — secretos / API keys
- `out/` — salidas de jobs / JSON de prueba
- `node_modules/`, `apps/web/dist/` — dependencias y build
- `db/*.sqlite*` — bases locales

Esos archivos **no aparecen** en `git add -A`. Si necesitás documentar variables, usá `.env.example` (sin secretos).

**Comprobar si un path está ignorado:**

```bash
git check-ignore -v ruta/al/archivo
```

### 3. Archivos nuevos jamás “add”eados

Siguen como *untracked* hasta que los agregás. **`git status`** lista “Untracked files”.

---

## Flujo habitual: llevar todo lo rastreable al remoto

Desde la **raíz del repo** (`cd` al directorio donde está `.git/`):

```bash
git branch --show-current          # confirmar rama
git status                         # qué cambió / qué falta staged
git add -A                         # staged: cambios + borrados + nuevos (respeta ignore)
git status                         # revisar lista verde (staged)
git commit -m "mensaje claro"
git push origin "$(git branch --show-current)"
```

Si es la **primera vez** que subís esa rama al remoto:

```bash
git push -u origin nombre-de-la-rama
```

`-u` guarda el tracking: después alcanza con `git push`.

---

## Comandos que suele usar el mismo flujo que en el chat

**Ver estado y diferencias:**

```bash
git status -sb                     # corto + rama vs origin
git diff --stat                    # resumen de cambios unstaged
git diff --cached --stat           # resumen de lo ya staged
git log --oneline -10              # últimos commits
```

**Desde el remoto (antes de pushear o para actualizar):**

```bash
git fetch origin
git status                         # ¿“ahead” / “behind”?
git pull --rebase origin TU-RAMA   # opcional si trabajan en equipo
```

**Revertir staged sin perder trabajo en archivo:**

```bash
git restore --staged archivo     # saca del stage, el archivo sigue editado
```

---

## Checks antes de pensar que “Git falló”

1. ¿Estabas en la **rama** que creías? (`git branch --show-current`)
2. ¿Pusiste a **`origin`** la misma rama? (`git push origin TU-RAMA`)
3. ¿Los archivos “faltantes” están en **`out/`**, son **`.env`**, o **`node_modules`**? → ignorados por regla del proyecto.
4. ¿Solo hiciste **`git add` parcial**? → volvé a `git add -A` desde la raíz del repo.

---

## Referencia local en este repo

- Ignore global del monorepo: [.gitignore](../../.gitignore) en la raíz del proyecto.
- Para variables: **no** commit `.env`; sí **`.env.example`** cuando agreguen claves nuevas sin valores secretos.

---

## Una línea útil si “quiero todo lo no ignorado ya”

```bash
git add -A && git status
```

Si algo importante no aparece para commitear, pasá `git check-ignore -v` sobre esa ruta antes de forzar `git add -f` (solo si realmente debe versionarse y el equipo lo acordó).
