# Decisiones de diseño del modelo

Este documento registra las reglas acordadas para construir el programador de inspecciones de forma incremental y controlada.

## Estado actual

Fase 2 — definición del programador básico.

## Reglas confirmadas

### Jornada
- Jornada objetivo: 10:00 a 18:00.
- Duración objetivo diaria: 8 horas por auditor.
- Superar 8 horas está permitido cuando sea necesario.
- El excedente de jornada debe penalizarse en la función objetivo, no prohibirse.

### Tipos de actividad
- Inspección Física: requiere 2 auditores.
- Proyecto: requiere 1 auditor.
- El auditor indicado en la columna `Auditor` del Excel es responsable obligatorio de su actividad.
- En una inspección Física, el modelo asigna un segundo auditor acompañante.

### Varias actividades en un día
- Un auditor puede participar en varias actividades el mismo día.
- La carga diaria debe buscar mantenerse dentro de 8 horas, aunque puede excederse con penalización.

### Traslados
- En la primera versión no se incorporan tiempos de traslado.
- La cercanía entre actividades sí se utilizará para elegir parejas.
- La cercanía se medirá inicialmente mediante distancia Haversine usando latitud y longitud.

### Horizonte de programación
- El modelo determina el número de días necesario.
- Los días se expresan inicialmente como Día 1, Día 2, Día 3, etc.
- No se fija manualmente un número de días.
- El objetivo es encontrar un número de días viable con buena distribución de carga, no simplemente comprimir todas las actividades al mínimo matemático.

## Lógica de parejas

### Regla general
- En la primera versión se trabajará con parejas de auditores.
- Las parejas deben buscar compatibilidad geográfica entre las actividades propias de ambos auditores.
- Si dos actividades tienen la misma ubicación, esa combinación debe considerarse especialmente favorable.
- Entre ubicaciones distintas, se debe preferir la menor distancia Haversine.

### Reciprocidad
- Si A y B forman pareja y ambos tienen inspecciones físicas, pueden acompañarse mutuamente.
- Si A tiene dos inspecciones físicas y B una, B puede acompañar a A en ambas si la carga total lo permite.
- No se exige reciprocidad uno-a-uno.

### Auditor sin actividad propia
- Se prefiere como acompañante a un auditor que tenga actividad propia ese mismo día y cuya ruta sea geográficamente compatible.
- Un auditor sin actividad propia sí puede utilizarse como acompañante.
- Utilizar un auditor sin actividad propia debe penalizarse, no prohibirse.
- Debe recurrirse a esta opción cuando no exista una alternativa mejor con actividad propia ese día.

### Proyectos y físicas
- Si una pareja tiene Proyecto e Inspección Física, se debe preferir el orden Proyecto → Física.
- Este orden es una preferencia, no una restricción absoluta.
- Si ambos auditores tienen Proyecto, pueden revisar sus respectivos proyectos durante ese periodo.
- Para esta versión se asume que las actividades de tipo Proyecto se realizan en la misma ubicación común, por lo que pueden ejecutarse en paralelo sin romper la coherencia logística de la pareja.
- Si solo uno tiene Proyecto, el otro puede apoyarlo en esa revisión como caso especial.
- Posteriormente pueden continuar juntos con una inspección Física compatible.

## Mejora futura registrada

### Equipos de 3 auditores
Una vez que la versión basada en parejas sea funcional y validada, evaluar una extensión del modelo para permitir equipos de 3 auditores.

Ejemplo de uso potencial:
- tres auditores con actividades geográficamente muy cercanas;
- dos realizan una inspección Física mientras el tercero atiende un Proyecto cercano;
- posteriormente se reorganiza el equipo para las siguientes actividades.

Esta mejora no se implementará en la primera versión, pero debe retomarse expresamente cuando el modelo por parejas haya sido validado.
