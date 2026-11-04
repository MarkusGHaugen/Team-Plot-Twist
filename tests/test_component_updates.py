def test_component_cache_reloads_changed_files_without_restart(tmp_path, monkeypatch):
    import app
    calls=[]
    def component(**kwargs):
        calls.append(kwargs)
        return kwargs['js']+'|'+kwargs['css']
    monkeypatch.setattr(app,'COMPONENT_DIR',tmp_path)
    monkeypatch.setattr(app.st.components.v2,'component',component)
    for name in ('game.html','game.css','game.js','browser_identity.js','browser_backup.js'):
        (tmp_path/name).write_text('original')
    app.cached_component.clear()
    try:
        assert app.game_component()=='original|original'
        assert app.game_component()=='original|original'
        assert len(calls)==1
        (tmp_path/'game.js').write_text('updated stair controls')
        assert app.game_component()=='updated stair controls|original'
        (tmp_path/'game.css').write_text('updated style')
        assert app.game_component()=='updated stair controls|updated style'
        assert app.browser_identity_component()=='original|'
        (tmp_path/'browser_identity.js').write_text('English language settings')
        assert app.browser_identity_component()=='English language settings|'
    finally:
        app.cached_component.clear()
