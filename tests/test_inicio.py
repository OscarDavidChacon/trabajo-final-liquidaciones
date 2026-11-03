"""Prueba de humo: la app se crea y la ruta / responde."""

from app import create_app


def test_raiz_responde():
    app = create_app()
    cliente = app.test_client()
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert "Pipeline_Liquidaciones_Ganado" in respuesta.get_data(as_text=True)
