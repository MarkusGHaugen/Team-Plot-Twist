import re


def test_component_cache_reloads_changed_files_without_restart(tmp_path, monkeypatch):
    import app
    calls=[]
    def component(**kwargs):
        calls.append(kwargs)
        return kwargs['js']+'|'+kwargs['css']
    build=tmp_path/'build'
    monkeypatch.setattr(app,'COMPONENT_DIR',tmp_path)
    monkeypatch.setattr(app,'STATIC_BUILD_DIR',build)
    monkeypatch.setattr(app.st.components.v2,'component',component)
    for name in ('game.html','game.css','game.js','browser_identity.js','browser_backup.js'):
        (tmp_path/name).write_text('original')

    def served_game():
        loader,css=app.game_component().split('|')
        url=re.search(r'"(app/static/build/[^"]+)"',loader).group(1)
        return (build/url.rsplit('/',1)[1]).read_text(),css,loader

    app.cached_component.clear()
    try:
        assert served_game()[:2]==('original','original')
        first_loader=served_game()[2]
        assert len(calls)==1
        (tmp_path/'game.js').write_text('updated stair controls')
        game,css,loader=served_game()
        assert (game,css)==('updated stair controls','original') and loader!=first_loader
        assert len(list(build.glob('game-*.js')))==1, 'old game versions are removed'
        (tmp_path/'game.css').write_text('updated style')
        assert served_game()[:2]==('updated stair controls','updated style')
        assert app.browser_identity_component()=='original|'
        (tmp_path/'browser_identity.js').write_text('English language settings')
        assert app.browser_identity_component()=='English language settings|'
    finally:
        app.cached_component.clear()


def test_the_game_code_is_not_inlined_in_every_run(tmp_path, monkeypatch):
    import app
    monkeypatch.setattr(app,'STATIC_BUILD_DIR',tmp_path)
    monkeypatch.setattr(app.st.components.v2,'component',lambda **kwargs: kwargs)
    app.cached_component.clear()
    try:
        sent=app.game_component()
        game=(app.COMPONENT_DIR/'game.js').read_text()
        assert len(sent['js'])<1500<len(game)
        assert 'import(source)' in sent['js'] and 'export default function' in sent['js']
    finally:
        app.cached_component.clear()
