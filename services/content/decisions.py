"""ÚNICO archivo de código que deben modificar los estudiantes.
Decisiones implementadas (ver entrega/ADR-001.md):
  1. Control optimista de versiones atómico en MongoDB.
  2. Escrituras autorizadas solo con la fuente autoritativa (Gestión/PostgreSQL).
  3. Presencia efímera con TTL en una sola escritura y degradación si Redis falla.
"""
from pymongo import ReturnDocument
from redis.exceptions import RedisError


def save_board(collection, board_id, expected_version, title):
    # TODO 1: la versión esperada forma parte del filtro de la MISMA operación
    # find_one_and_update. MongoDB garantiza atomicidad a nivel de documento:
    # solo una de dos escrituras concurrentes con la misma versión coincide con
    # el filtro; la otra no encuentra documento y retorna None (la API -> 409).
    return collection.find_one_and_update(
        {'_id': board_id, 'version': expected_version},
        {'$set': {'title': title}, '$inc': {'version': 1}},
        return_document=ReturnDocument.AFTER,
    )


def permission_for_write(user, board_id, cached_permission, authoritative_permission):
    # TODO 2: una escritura es una operación crítica. La caché (TTL 60 s) solo
    # sirve para la interfaz; no prueba que la concesión siga vigente. Se consulta
    # siempre a Gestión (PostgreSQL). Si la autoridad falla, authoritative_permission
    # lanza HTTPException(503) y se deja propagar: nunca se usa una concesión vieja.
    # Costo: una llamada HTTP + consulta SQL extra por escritura.
    return authoritative_permission(user, board_id)


def touch_presence(client, key, ttl):
    # TODO 3: SET con EX en una única escritura atómica: crea o renueva la clave
    # y su expiración a la vez (no hay ventana sin TTL como con SET + EXPIRE).
    # Si Redis no responde, la presencia se degrada (False) sin afectar ediciones.
    try:
        client.set(key, 'online', ex=ttl)
        return True
    except RedisError:
        return False
