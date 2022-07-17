# PfadiTag Registration
Eine Python WebApp zur Registrierung und Verwaltung von Events im Rahmen des PfadiTags

## Migrate Database changes

Short: `flask db migrate` and `flask db upgrade`.

```
$ flask db migrate -m "lat/lon"    
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.autogenerate.compare] Detected added column 'event.lat'
INFO  [alembic.autogenerate.compare] Detected added column 'event.lon'
  Generating /Users/hoechst/Projects/pfaditag-registration/migrations/versions/cf3b00d56bd6_lat_lon.py ...  done

$ flask db upgrade
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 588a003602ed -> cf3b00d56bd6, lat/lon
```

## Query LAT/LON from addr

```js
{% for group in groups %}
$.get('https://nominatim.openstreetmap.org/search?format=json&q={{ group.street }}, {{ group.zip }} {{ group.city }}', function(data){
    var marker_group_{{ group.id }} = L.marker([data[0].lat, data[0].lon], { icon: groupStyle }).addTo(map);
});
{% endfor %}
```

## Rebuild Bootstrap 

Make sure, that all dependencies are installed:

```bash
$ cd bootstrap-5.2.0-beta1         
$ npm install 

up to date, audited 929 packages in 2s

138 packages are looking for funding
  run `npm fund` for details

12 vulnerabilities (7 moderate, 5 high)

To address issues that do not require attention, run:
  npm audit fix

Some issues need review, and may require choosing
a different dependency.

Run `npm audit` for details.
```

Build:

```bash
$ npm run dist

> bootstrap@5.2.0-beta1 dist
> npm-run-all --aggregate-output --parallel css js
...
```

The resulting bootstrap.min.css file is symlinked into the project and is not required to be copied over.

## Shoutouts

- [The Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world) by Miguel Grinberg
