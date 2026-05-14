import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


async def _renew_all_subscriptions_async():
    try:
        # Lazy import to avoid circular dependencies
        from storage import _items
        from connectors.base import ConnectorConfig, ConnectorRegistry
    except Exception as e:
        logger.exception('Scheduler imports failed: %s', e)
        return

    logger.info('Starting renewal job at %s', datetime.utcnow().isoformat())
    for item_id, item in list(_items.items()):
        try:
            cfg = item.get('config', {})
            tenant_id = item.get('tenant_id')
            cconfig = ConnectorConfig(
                tenant_id=tenant_id,
                item_id=item_id,
                source_system=cfg.get('source_system') or cfg.get('source'),
                base_url=cfg.get('base_url', ''),
                company_id=cfg.get('company_id'),
                entities=cfg.get('entities', []),
            )
            adapter = ConnectorRegistry.create(cconfig)
            result = adapter.renew_subscriptions()
            if hasattr(result, '__await__'):
                await result
            logger.info('Renewed subscriptions for item %s', item_id)
        except Exception as e:
            logger.exception('Failed renewing subscriptions for item %s: %s', item_id, e)


def _run_async_job(coro):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(coro)
    else:
        loop.run_until_complete(coro)


def start_scheduler():
    # Run every 2 days
    scheduler.add_job(lambda: _run_async_job(_renew_all_subscriptions_async()), 'interval', days=2, id='renew_subscriptions')
    scheduler.start()
    logger.info('Scheduler started with renew_subscriptions job')


def stop_scheduler():
    try:
        scheduler.shutdown()
    except Exception:
        pass
