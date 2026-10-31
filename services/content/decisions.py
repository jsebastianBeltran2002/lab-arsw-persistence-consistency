"""ÚNICO archivo de código que deben modificar los estudiantes.
Decisiones del equipo explicadas en entrega/ADR-001.md.
"""
from pymongo import ReturnDocument
from redis.exceptions import RedisError


def save_board(collection, board_id, expected_version, title):
    # TODO 1: la versión esperada va en el filtro de la misma operación.
    # Si otro usuario ya cambió esa versión no hay coincidencia y se retorna None, la API responde 409.
    return collection.find_one_and_update(
        {'_id': board_id, 'version': expected_version},
        {'$set': {'title': title}, '$inc': {'version': 1}},
        return_document=ReturnDocument.AFTER,
    )


def permission_for_write(user, board_id, cached_permission, authoritative_permission):
    # TODO 2: para escribir siempre se consulta a Gestión, la caché solo sirve para la interfaz.
    # Si Gestión no responde se deja pasar el error y la API responde 503 sin guardar.
    return authoritative_permission(user, board_id)


def touch_presence(client, key, ttl):
    # TODO 3: valor y expiración en una sola escritura, cada heartbeat renueva el TTL.
    # Si Redis falla la presencia se degrada y se retorna False.
    try:
        client.set(key, 'online', ex=ttl)
        return True
    except RedisError:
        return False
