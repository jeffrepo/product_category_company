# Categorías de producto por compañía — Odoo 19

Nombre técnico: `product_category_company`  
Versión: `19.0.1.0.1`  
Dependencia: `product`. Instalación habilitada.

Módulo reutilizable en Odoo 19, sin dependencia de `gdomex`.

## Funcionamiento

- Cada categoría tiene una compañía obligatoria. Las categorías nuevas toman
  la compañía activa del usuario.
- Los usuarios acceden únicamente a las categorías de su compañía activa,
  incluso si tienen varias compañías seleccionadas. La regla se aplica a
  lectura, creación, modificación y eliminación, también mediante API.
- Las categorías padre e hijas deben pertenecer a la misma compañía.
- El campo Compañía aparece en el formulario y la lista para usuarios con
  acceso a varias compañías. La lista permite editar la compañía en bloque.
- Los productos nuevos conservan el comportamiento de Odoo 19: la categoría
  es opcional. Un valor predeterminado de la compañía activa se conserva; uno
  de otra compañía se limpia para que el usuario seleccione una categoría
  válida. No se elige ni se crea una categoría automáticamente.
- La expansión de grupos vacíos en las vistas de productos respeta los
  permisos de las categorías.

El modo superusuario y `sudo()` omiten las reglas de acceso de Odoo. Las
validaciones de jerarquías se mantienen en esos modos.

## Asignación de categorías existentes

**La distribución de las categorías entre compañías corresponde al cliente,
manualmente o mediante su propio script.**

En la primera instalación, Odoo inicializa el nuevo campo obligatorio de las
categorías existentes con la compañía del entorno de instalación. En una
compilación de Odoo.sh puede ser la compañía principal del administrador.
Esta asignación inicial permite instalar el módulo; no deduce a qué compañía
pertenece realmente cada categoría a partir de sus productos.

1. Instalar primero en la base de pruebas del cliente.
2. Seleccionar la compañía que recibió las categorías al instalar. Un
   administrador también puede usar el modo superusuario para la asignación.
3. Abrir Categorías de producto y asignar la compañía correspondiente desde
   el formulario o seleccionando varias categorías en la lista y editando
   la columna Compañía.
4. Mover padres e hijas a la misma compañía en una única operación. Si una
   categoría debe quedar en una compañía distinta de su padre, desvincular
   primero esa relación y reorganizar la jerarquía.
5. Después de reasignar, cambiar a la compañía de destino para ver la
   categoría. Revisar también los productos que la utilizan.

El módulo no modifica la compañía ni la categoría de los productos existentes,
no duplica categorías y no reparte automáticamente el catálogo. El cliente
debe completar la correspondencia entre productos y categorías antes de usar
los procesos habituales en cada compañía. Los productos compartidos mantienen
una única categoría estándar; no se les añade una categoría por compañía.

## Instalación en Odoo.sh

Los archivos del módulo están directamente en la raíz de este repositorio.
Integrarlo en el proyecto principal como submódulo o carpeta con el nombre
`product_category_company`, de modo que la ruta del manifiesto sea
`product_category_company/__manifest__.py`.

Enviar el cambio a la rama de pruebas y, cuando termine la compilación,
actualizar la lista de aplicaciones en modo desarrollador. Quitar el filtro
Aplicaciones, buscar `product_category_company` e instalarlo. Si ya estaba
instalado, actualizarlo.

## Validación

Se verificaron la sintaxis de Python, XML y las referencias a las vistas
nativas de Odoo 19. Se incluyen pruebas de integración para el aislamiento,
cambio de compañía activa, jerarquías, asignación manual y valores
predeterminados de productos.

Las pruebas funcionales y de integración en Odoo quedan a cargo del cliente
en su base de test; no se han ejecutado en este entorno.

```text
odoo-bin -d BASE_DE_PRUEBAS -i product_category_company --test-enable --test-tags /product_category_company --stop-after-init
```

Para una base que ya tiene el módulo instalado, sustituir `-i` por `-u`.
Comprobar también en la interfaz que, al cambiar de compañía, cambian las
categorías disponibles y que los productos existentes quedaron vinculados a
las categorías correctas después de la asignación del cliente.

Licencia: LGPL-3.
