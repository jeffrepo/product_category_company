# Domex: Categorías compartidas y Vinyasa

Módulo para **Odoo 19**, versión **19.0.2.0.0**. Conserva el nombre técnico
`product_category_company` para actualizar la instalación existente. Depende
de `product` y se combina con `domex_product_warehouse_access` cuando está instalado.

## Acceso

| Usuario | Categorías compartidas | Categorías Vinyasa |
| --- | --- | --- |
| Sin grupo Vinyasa | Sí | No |
| Con grupo Vinyasa | Sí | Sí |
| Cuenta principal de administrador (`base.user_admin`) | Sí | Sí |

El acceso requiere los permisos nativos del modelo. La excepción identifica
a la cuenta principal por su ID externo. Otros administradores de Ajustes
necesitan el grupo Vinyasa para ver las categorías restringidas.

Las categorías sin marcar se comparten entre compañías. **Vinyasa** se marca
manualmente: no se deduce del nombre ni de una compañía. El grupo no concede
acceso a la compañía Vinyasa, a sus almacenes o a funciones de administración.

Una categoría marcada restringe también a todas sus subcategorías, incluso
si estas tienen su propio checkbox desmarcado. El campo calculado **Acceso
Vinyasa requerido** muestra el resultado de la marca propia y la heredada.
Al quitar una marca del padre se recalcula el acceso de sus descendientes;
las categorías con una marca propia siguen restringidas.

## Productos, almacenes y multicompañía

Los productos y variantes de una categoría Vinyasa requieren también ese
grupo. Esto evita ofrecer productos cuya categoría el usuario no puede leer.
Los productos sin categoría conservan sus otras restricciones de acceso.

Las reglas de este módulo son globales y se intersectan con las demás:

- Un producto Vinyasa con almacenes requiere el grupo **Vinyasa**, un almacén
  coincidente y una compañía seleccionada, según `domex_product_warehouse_access`.
- Un producto contable en una categoría Vinyasa requiere **Producto contable**
  y **Vinyasa**, además de la compañía aplicable. El grupo Vinyasa por sí solo
  no concede acceso a productos contables.
- La cuenta principal conserva la excepción de ambos módulos, respetando las
  reglas nativas de compañía de productos y cualquier otra regla externa.
- Cambiar la compañía seleccionada no oculta las categorías compartidas.
  Las cuentas, valoración y otras propiedades dependientes de compañía
  conservan el comportamiento nativo de Odoo y sus datos existentes.

La restricción se aplica al ORM/API, listas, búsquedas, selectores de facturas,
lectura directa y operaciones de edición. No es un filtro únicamente visual.
Los permisos de documentos históricos siguen siendo los de sus módulos:
el grupo no da acceso a facturas, movimientos ni documentos de otras compañías.
Como en Odoo estándar, `sudo()` y el modo superusuario omiten las reglas.

## Configuración

1. Actualizar **product_category_company** en la base de pruebas.
2. Con la cuenta principal, abrir **Categorías de producto** y marcar
   **Vinyasa** en las categorías que correspondan. Puede marcarse un padre
   para proteger toda su jerarquía. La lista permite edición en bloque.
3. En **Ajustes → Usuarios → Permisos de acceso**, asignar **Vinyasa** en
   **Domex: Categorías Vinyasa** a los usuarios autorizados.
4. Conservar las asignaciones de almacenes, compañías y Producto contable
   necesarias. Volver a abrir las vistas para descartar datos que el navegador
   ya tenía cargados.

Solo los administradores de Ajustes pueden editar la clasificación, también
en importaciones y API. Los demás usuarios pueden editar los datos para los
que ya tengan permisos, pero no cambiar el nivel de protección mediante la
categoría padre o la categoría del producto. Tampoco pueden duplicar categorías
restringidas ni eliminar una categoría que contenga categorías Vinyasa: la
eliminación podría quitar categorías a productos y dejar de protegerlos.

## Actualización desde 19.0.1.0.1

Esta versión **reemplaza el aislamiento de categorías por compañía** por
categorías compartidas con una excepción de acceso Vinyasa.

- Se reutiliza `product_category_active_company_rule` para reemplazar su
  dominio anterior. No quedan las dos restricciones de este módulo activas
  simultáneamente. Las reglas ajenas al módulo no se modifican.
- Las categorías existentes comienzan sin marcar y quedan compartidas.
  La actualización no marca automáticamente las categorías de la compañía
  Vinyasa ni asigna usuarios al grupo.
- Se preservan los IDs, nombres, jerarquías, productos y propiedades contables.
- La columna anterior `company_id` se conserva, ahora opcional, como referencia
  histórica. No se vacía ni se usa para determinar visibilidad. Se retira de
  las vistas de configuración para que no se confunda con el control Vinyasa.
- Las categorías nuevas no reciben una compañía por defecto. Padres e hijas
  pueden tener asignaciones históricas distintas sin impedir su uso compartido.

Actualizar el módulo instalado; **no desinstalarlo** para hacer este cambio.
Un push al repositorio solo entrega el código: la base debe actualizar las
vistas, campos y reglas mediante la actualización del módulo.

## Pruebas

La suite cubre categorías compartidas, jerarquías, búsquedas y lectura directa,
la excepción de la cuenta principal, cambios de grupo y clasificación,
protección de importaciones y modificaciones de jerarquía, productos y variantes,
compañías de productos, valores predeterminados y expansión de categorías.
Si está instalado el módulo de almacenes, también comprueba la combinación
con almacenes y productos contables.

En una base de pruebas de Odoo 19:

```sh
odoo-bin -d BASE_DE_PRUEBAS -u product_category_company --test-enable --test-tags /product_category_company --stop-after-init
```

Para validar ambos módulos juntos, instalarlos en una base de pruebas y
ejecutar las suites de ambos. En una instalación nueva usar `-i` en vez de `-u`.

La revisión local verifica sintaxis, XML, referencias, XPath y lógica aislada.
Las pruebas de integración requieren Odoo y PostgreSQL, no disponibles en
el entorno local donde se preparó este cambio.

Licencia: LGPL-3.
