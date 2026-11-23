import re
import unicodedata
from collections import Counter
from decimal import Decimal

from models.comparacion import ComparacionNueva, OfertaComparacionNueva
from repositories.comparacion_repository import ComparacionRepository


def _decimal(valor):
    if valor is None:
        return Decimal('0')
    return Decimal(str(valor))


def _clave_producto(codigo, producto):
    codigo = str(codigo or '').strip()
    if not codigo or codigo == '-':
        texto = str(producto or '')
        prefijo = 'nombre'
    else:
        texto = codigo
        prefijo = 'codigo'
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(char for char in texto if not unicodedata.combining(char))
    normalizado = re.sub(r'[^a-z0-9]+', ' ', texto.lower()).strip()
    return f'{prefijo}:{normalizado}' if normalizado else prefijo


class ComparacionService:
    def __init__(self, repositorio=None):
        self._repositorio = repositorio if repositorio is not None else ComparacionRepository()

    def guardar(
        self,
        nombre,
        tipo_productos,
        id_usuario,
        ids_importacion,
        decision,
        matrix_rows_data,
        razones,
    ):
        if id_usuario is None or not ids_importacion or not matrix_rows_data:
            return None
        ofertas = self._repositorio.obtener_ofertas_guardadas(ids_importacion)
        if not ofertas:
            return None
        claves = {}
        mejores = {}
        for fila in matrix_rows_data:
            oferta = next(iter(fila.get('offers', {}).values()), None)
            if oferta is None:
                continue
            clave = _clave_producto(oferta.get('code'), oferta.get('product'))
            claves[clave] = fila
            mejores[clave] = fila.get('best_provider')

        recomendado = str(decision.get('recommended') or '')
        detalles = []
        costo_recomendado = Decimal('0')
        costo_combinada = Decimal('0')
        for oferta in ofertas:
            clave = _clave_producto(oferta['codigo'], oferta['producto'])
            if clave not in claves:
                continue
            precio = _decimal(oferta['precio_unitario'])
            cantidad = max(1, int(oferta['compra_minima'] or 1))
            seleccionada = oferta['proveedor'] == mejores.get(clave)
            if oferta['proveedor'] == recomendado:
                costo_recomendado += precio
            if seleccionada:
                costo_combinada += precio
            detalles.append(
                OfertaComparacionNueva(
                    id_detalle_cotizacion=oferta['id_detalle_cotizacion'],
                    proveedor=oferta['proveedor'],
                    producto=oferta['producto'],
                    codigo=oferta['codigo'],
                    categoria=oferta['categoria'] or claves[clave].get('category', ''),
                    precio_evaluado=precio,
                    cantidad_requerida=cantidad,
                    costo_total_linea=precio * cantidad,
                    oferta_valida=True,
                    seleccionado_combinada=seleccionada,
                    observacion=(
                        f"Entrega: {oferta['entrega_dias']} d; "
                        f"descuento: {_decimal(oferta['descuento_porcentaje'])}"
                    ),
                )
            )
        if not detalles:
            return None

        ahorro = _decimal(decision.get('advantage'))
        comparacion = ComparacionNueva(
            nombre=nombre,
            tipo_productos=tipo_productos,
            id_usuario=id_usuario,
            id_proveedor_recomendado=self._repositorio.obtener_id_proveedor(recomendado),
            proveedor_recomendado_nombre=recomendado,
            estado='completada',
            costo_proveedor_recomendado=costo_recomendado,
            costo_compra_combinada=costo_combinada,
            costo_referencia=costo_recomendado + ahorro,
            ahorro_estimado=ahorro,
            justificacion='\n'.join(razones or []),
            detalles=detalles,
        )
        return self._repositorio.guardar(comparacion)

    @staticmethod
    def _matriz_desde_ofertas(ofertas):
        agrupado = {}
        for oferta in ofertas:
            clave = _clave_producto(oferta['codigo'], oferta['producto'])
            grupo = agrupado.setdefault(
                clave,
                {
                    'product': oferta['producto'],
                    'category': oferta['categoria'],
                    'offers': {},
                },
            )
            grupo['offers'][oferta['proveedor']] = {
                'code': oferta['codigo'],
                'product': oferta['producto'],
                'price': _decimal(oferta['precio_unitario']),
            }
        matriz = []
        for grupo in agrupado.values():
            mejor = min(grupo['offers'].items(), key=lambda item: item[1]['price'])
            matriz.append({
                'product': grupo['product'],
                'category': grupo['category'],
                'offers': grupo['offers'],
                'best_price': mejor[1]['price'],
                'best_provider': mejor[0],
            })
        return matriz

    @staticmethod
    def _decision_desde_matriz(matriz):
        if not matriz:
            return None
        proveedores = sorted({
            proveedor
            for fila in matriz
            for proveedor in fila['offers']
        })
        if not proveedores:
            return None
        wins = Counter(fila['best_provider'] for fila in matriz)
        sumas = {proveedor: Decimal('0') for proveedor in proveedores}
        conteos = Counter()
        for fila in matriz:
            for proveedor, oferta in fila['offers'].items():
                precio = _decimal(oferta.get('price'))
                sumas[proveedor] += precio
                conteos[proveedor] += 1
        promedios = {
            proveedor: sumas[proveedor] / conteos[proveedor]
            for proveedor in proveedores
            if conteos[proveedor]
        }
        recomendado = min(
            proveedores,
            key=lambda proveedor: (-wins[proveedor], promedios.get(proveedor, Decimal('0')), proveedor),
        )
        ventaja = Decimal('0')
        for fila in matriz:
            if fila['best_provider'] != recomendado:
                continue
            precios = sorted(
                _decimal(oferta.get('price'))
                for oferta in fila['offers'].values()
                if oferta.get('price') is not None
            )
            if len(precios) > 1:
                ventaja += precios[1] - precios[0]
        return {
            'recommended': recomendado,
            'wins': wins[recomendado],
            'product_count': len(matriz),
            'provider_count': len(proveedores),
            'average': promedios.get(recomendado, Decimal('0')),
            'advantage': ventaja,
        }

    def sincronizar_desde_importaciones(self, id_usuario):
        if id_usuario is None:
            return None
        ids = self._repositorio.obtener_importaciones_sin_comparacion(id_usuario)
        ofertas = self._repositorio.obtener_ofertas_guardadas(ids)
        if len({oferta['proveedor'] for oferta in ofertas}) < 2:
            return None
        matriz = self._matriz_desde_ofertas(ofertas)
        decision = self._decision_desde_matriz(matriz)
        if decision is None:
            return None
        categoria = Counter(
            oferta['categoria']
            for oferta in ofertas
            if oferta.get('categoria')
        ).most_common(1)
        razones = [
            f"Obtuvo el mejor precio en {decision['wins']} de "
            f"{decision['product_count']} productos comparados.",
            'Comparación generada a partir de importaciones confirmadas previamente.',
        ]
        return self.guardar(
            f"Comparación de {len(ids)} proveedores",
            categoria[0][0] if categoria else '',
            id_usuario,
            ids,
            decision,
            matriz,
            razones,
        )

    def editar(self, id_comparacion, id_usuario, nombre, tipo_productos, justificacion):
        if id_comparacion is None or id_usuario is None:
            return None
        actualizadas = self._repositorio.actualizar(
            id_comparacion,
            id_usuario,
            nombre,
            tipo_productos,
            justificacion,
        )
        return id_comparacion if actualizadas else None

    def eliminar(self, id_comparacion, id_usuario):
        if id_comparacion is None or id_usuario is None:
            return None
        eliminadas = self._repositorio.eliminar(id_comparacion, id_usuario)
        return id_comparacion if eliminadas else None

    def listar(self, id_usuario, busqueda='', categoria='', proveedor='', fecha=''):
        return self._repositorio.listar(
            id_usuario,
            busqueda=busqueda,
            categoria=categoria,
            proveedor=proveedor,
            fecha=fecha,
        )

    def obtener_detalle(self, id_comparacion, id_usuario=None):
        return self._repositorio.obtener_detalle(id_comparacion, id_usuario)


__all__ = ['ComparacionService']
