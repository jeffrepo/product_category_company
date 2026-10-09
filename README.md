# product_category_company — Odoo 19.0

**Estado: borrador para revisión. No instalar todavía en una base existente.**

Módulo genérico, sin dependencia de `gdomex`, para asignar una compañía a
cada categoría de producto y limitar su acceso a la compañía activa.
Seleccionar varias compañías en el selector no amplía las categorías visibles.

## Preparado

- Campo obligatorio `company_id`, con la compañía activa como valor inicial.
- Regla global para lectura, creación, modificación y eliminación.
- Validación de compañía entre categorías padre e hijas.
- Campo de compañía en el formulario y la lista.
- Nueve pruebas de integración de acceso, selección de compañía y jerarquías.
- Identificadores de vistas y puntos de extensión verificados contra
  [el código oficial de Odoo 19.0](https://github.com/odoo/odoo/blob/19.0/addons/product/views/product_category_views.xml).

Como en las demás reglas de Odoo, el modo superusuario y `sudo()` omiten las
reglas de acceso. Las validaciones de jerarquías se mantienen en esos modos.

## Pendiente antes de habilitar la instalación

1. Confirmar si los productos existentes tienen compañía o son compartidos.
   Un producto compartido tiene una única categoría estándar: restringir esa
   categoría a una compañía puede causar errores de acceso desde las demás.
   No se han reasignado productos ni duplicado categorías automáticamente.
2. Definir la migración de las categorías existentes y la categoría inicial
   de productos nuevos para cada compañía.
3. Ejecutar las pruebas en una base temporal de Odoo 19 y probar la instalación.

La sintaxis de Python y XML se verificó localmente. Este entorno no dispone
de Odoo ni PostgreSQL, por lo que las pruebas de integración no se han ejecutado.

El manifiesto mantiene `installable=False` hasta completar esos pendientes.
