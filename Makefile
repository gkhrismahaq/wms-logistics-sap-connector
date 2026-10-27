WEB_DB_NAME = wms_logistics_dev
DB_USER = odoo
DB_PASSWORD = odoo
DOCKER = docker
DOCKER_COMPOSE = ${DOCKER} compose
CONTAINER_ODOO = wms-odoo
CONTAINER_DB = wms-postgres

help:
	@echo "Available commands for WMS Logistics SAP Connector:"
	@echo "  start               - Start containers in background"
	@echo "  stop                - Stop containers"
	@echo "  restart             - Restart containers"
	@echo "  wait-db             - Wait until PostgreSQL is ready to accept connections"
	@echo "  console             - Open Odoo shell in Odoo container"
	@echo "  psql                - Open PostgreSQL shell in DB container"
	@echo "  logs odoo           - Tail logs for Odoo container"
	@echo "  logs db             - Tail logs for DB container"
	@echo "  addon <addon_name>  - Upgrade specified addon and reload Odoo"

start:
	$(DOCKER_COMPOSE) up -d

stop:
	$(DOCKER_COMPOSE) down

wait-db:
	@echo "Checking PostgreSQL readiness..."
	@$(DOCKER) exec $(CONTAINER_DB) sh -c 'until pg_isready -U $(DB_USER) -d $(WEB_DB_NAME) -q; do sleep 0.5; done'
	@echo "PostgreSQL is ready."

restart:
	$(DOCKER_COMPOSE) restart
	@$(MAKE) wait-db

console:
	$(DOCKER) exec -it $(CONTAINER_ODOO) odoo shell --db_host=$(CONTAINER_DB) -d $(WEB_DB_NAME) -r $(DB_USER) -w $(DB_PASSWORD)

psql:
	$(DOCKER) exec -it $(CONTAINER_DB) psql -U $(DB_USER) -d $(WEB_DB_NAME)

define log_target
	@if [ "$(1)" = "odoo" ]; then \
		$(DOCKER) logs -f $(CONTAINER_ODOO); \
	elif [ "$(1)" = "db" ]; then \
		$(DOCKER) logs -f $(CONTAINER_DB); \
	else \
		echo "Invalid argument. Use 'odoo' or 'db'."; \
	fi
endef

logs:
	$(call log_target,$(word 2,$(MAKECMDGOALS)))

define upgrade_addon
	@if [ -z "$(1)" ]; then \
		echo "Error: Please specify addon name. Example: make addon wms_sap_connector"; \
		exit 1; \
	fi
	$(DOCKER) exec -i $(CONTAINER_ODOO) odoo --db_host=$(CONTAINER_DB) -d $(WEB_DB_NAME) -r $(DB_USER) -w $(DB_PASSWORD) -u $(1) --stop-after-init
endef

addon: wait-db
	$(call upgrade_addon,$(word 2,$(MAKECMDGOALS)))
	$(DOCKER_COMPOSE) restart odoo

e2e:
	@if [ -f .venv/bin/python ]; then \
		.venv/bin/python scripts/verify_e2e_integration.py; \
	else \
		python3 scripts/verify_e2e_integration.py; \
	fi

.PHONY: help start stop restart wait-db console psql logs odoo logs db addon e2e

# Catch-all rule to prevent make from failing on arguments passed to targets like 'addon'
%:
	@:
