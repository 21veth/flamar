"""Pestana de importacion de ventas."""

from views.import_shared import (
    BLUE,
    GREEN,
    ORANGE,
    PURPLE,
    ImportTab,
    RowError,
    header_indexes,
    parse_date,
    parse_number,
)


class SalesImportTab(ImportTab):
    TITLE = 'Importar datos de ventas'
    SUBTITLE = 'Carga el historial de ventas por producto desde Excel o CSV.'

    COLUMNS = (
        'Fecha',
        'Código del producto',
        'Producto',
        'Categoría',
        'Cantidad vendida',
        'Precio unitario',
        'Total de venta',
    )
    ALIASES = {
        'Código del producto': ('Codigo', 'Codigo producto', 'SKU', 'Codigo de producto'),
        'Cantidad vendida': ('Cantidad', 'Unidades', 'Unidades vendidas'),
        'Precio unitario': ('Precio', 'Precio venta', 'Precio de venta'),
        'Total de venta': ('Total', 'Importe', 'Subtotal'),
    }

    METRICS = (
        ('records', '▤', 'Registros', PURPLE, '#f0edff'),
        ('units', '▦', 'Unidades vendidas', GREEN, '#e8f8f1'),
        ('total', '$', 'Venta total', BLUE, '#eaf3ff'),
        ('products', '◈', 'Productos distintos', ORANGE, '#fff5e5'),
    )

    SAMPLE_ROWS = (
        ('05/08/2025', 'P001', 'Atun en lata 170 g', 'Conservas', '24', '5.50', '132.00'),
        ('05/08/2025', 'P002', 'Durazno en almibar 820 g', 'Conservas', '18', '8.90', '160.20'),
        ('06/08/2025', 'P003', 'Arroz extra 5 kg', 'Abarrotes', '30', '18.50', '555.00'),
        ('06/08/2025', 'P004', 'Azucar rubia 1 kg', 'Abarrotes', '40', '4.20', '168.00'),
        ('07/08/2025', 'P005', 'Aceite vegetal 1 L', 'Abarrotes', '22', '9.80', '215.60'),
        ('07/08/2025', 'P006', 'Leche evaporada 400 g', 'Lacteos', '35', '4.70', '164.50'),
        ('08/08/2025', 'P007', 'Atun en aceite 140 g', 'Conservas', '27', '6.20', '167.40'),
    )

    def preview_headers(self):
        return self.COLUMNS

    def sample_rows(self):
        return self.SAMPLE_ROWS

    def validate_data(self, data):
        errors = []
        indexes = header_indexes(data.headers, self.COLUMNS, self.ALIASES)
        for label in self.COLUMNS:
            if indexes[label] is None:
                errors.append(RowError('-', label, 'Columna requerida no encontrada'))
        if errors:
            return errors

        for number, row in enumerate(data.rows, start=2):
            fecha = parse_date(data.value(row, indexes['Fecha']))
            if fecha is None:
                errors.append(RowError(number, 'Fecha', 'Fecha invalida o vacia'))

            codigo = str(data.value(row, indexes['Código del producto'])).strip()
            if not codigo:
                errors.append(RowError(number, 'Código del producto', 'Codigo vacio'))

            cantidad = parse_number(data.value(row, indexes['Cantidad vendida']))
            if cantidad is None or cantidad <= 0:
                errors.append(RowError(number, 'Cantidad vendida', 'Debe ser un numero mayor a 0'))

            precio = parse_number(data.value(row, indexes['Precio unitario']))
            if precio is None or precio < 0:
                errors.append(RowError(number, 'Precio unitario', 'Debe ser un numero mayor o igual a 0'))

            total = parse_number(data.value(row, indexes['Total de venta']))
            if total is None or total < 0:
                errors.append(RowError(number, 'Total de venta', 'Debe ser un numero mayor o igual a 0'))
            elif cantidad is not None and precio is not None:
                if abs(total - cantidad * precio) > 0.01:
                    errors.append(RowError(
                        number,
                        'Total de venta',
                        'No coincide con cantidad x precio unitario',
                    ))
        return errors

    def compute_metrics(self, data):
        indexes = header_indexes(data.headers, self.COLUMNS, self.ALIASES)
        units = 0.0
        total = 0.0
        products = set()
        for row in data.rows:
            quantity = parse_number(data.value(row, indexes['Cantidad vendida']))
            price = parse_number(data.value(row, indexes['Precio unitario']))
            line_total = parse_number(data.value(row, indexes['Total de venta']))
            if quantity is not None:
                units += quantity
            if line_total is not None:
                total += line_total
            elif quantity is not None and price is not None:
                total += quantity * price
            code = str(data.value(row, indexes['Código del producto'])).strip()
            name = str(data.value(row, indexes['Producto'])).strip()
            if code or name:
                products.add(code or name)
        return {
            'records': f'{data.total:,}',
            'units': f'{units:,.0f}',
            'total': f'$ {total:,.2f}',
            'products': f'{len(products)}',
        }

    def process_summary(self, data):
        metrics = self.compute_metrics(data)
        return (
            f'Ventas procesadas: {metrics["records"]} registros, '
            f'{metrics["units"]} unidades y {metrics["total"]} en ventas.'
        )
