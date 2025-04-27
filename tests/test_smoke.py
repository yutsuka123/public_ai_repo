def test_import():
    import importlib
    mod = importlib.import_module("ai_repo")
    assert hasattr(mod, "__doc__")
