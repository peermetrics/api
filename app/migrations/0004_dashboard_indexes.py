from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Phase 0 indexes for the dashboard aggregation work (#20).

    Targets the queries run by the new /v1/conferences/summary endpoint
    and similar time-range dashboard queries:

    - conference(app_id, created_at): filter + GROUP BY for the summary
    - issue(conference_id, type): speeds up the EXISTS subqueries that
      classify conferences as has_error / has_warning
    - app_genericevent(app_id, created_at): future summary endpoints that
      group events by day (also helps cleanup_stale_conferences)
    """

    dependencies = [
        ('app', '0003_conference_unique_together'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='conference',
            index=models.Index(
                fields=['app', '-created_at'],
                name='idx_conf_app_created',
            ),
        ),
        migrations.AddIndex(
            model_name='issue',
            index=models.Index(
                fields=['conference', 'type'],
                name='idx_issue_conf_type',
            ),
        ),
        migrations.AddIndex(
            model_name='genericevent',
            index=models.Index(
                fields=['app', '-created_at'],
                name='idx_genevent_app_created',
            ),
        ),
    ]
