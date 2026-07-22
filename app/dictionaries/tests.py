# app/dictionaries/tests.py
import pytest
from django.db import IntegrityError, transaction
from .models import SystemType, Environment, BackupTool, InformationSystem
from api.v1.backup_operations.tests.factories import (
    SystemTypeFactory,
    EnvironmentFactory,
    BackupToolFactory,
    InformationSystemFactory
)

pytestmark = pytest.mark.django_db


class TestSystemType:
    
    def test_create_system_type(self):
        st = SystemTypeFactory(description="Тестовый тип системы")
        assert st.pk is not None
        assert st.name.startswith("type_")
        assert st.description == "Тестовый тип системы"

    def test_name_unique(self):
        SystemTypeFactory(name="PostgreSQL")
        with pytest.raises(IntegrityError):
            with transaction.atomic():  
                SystemTypeFactory(name="PostgreSQL")

    def test_str_returns_name(self):
        st = SystemTypeFactory(name="Kubernetes")
        assert str(st) == "Kubernetes"


class TestEnvironment:

    def test_create_environment(self):
        env = EnvironmentFactory(description="Продакшен")
        assert env.name.startswith("env_")
        assert env.description == "Продакшен"

    def test_name_unique(self):
        EnvironmentFactory(name="Production")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                EnvironmentFactory(name="Production")

    def test_str_returns_name(self):
        env = EnvironmentFactory(name="Development")
        assert str(env) == "Development"


class TestBackupTool:

    def test_create_backup_tool(self):
        tool = BackupToolFactory(description="Утилита бэкапа")
        assert tool.name.startswith("tool_")
        assert tool.is_active is True
        assert tool.description == "Утилита бэкапа"

    def test_str_returns_name(self):
        tool = BackupToolFactory(name="pg_dump")
        assert str(tool) == "pg_dump"


class TestInformationSystem:

    def test_create_information_system(self):
        isys = InformationSystemFactory(description="Ключевая система")
        assert isys.name.startswith("is_")
        assert isys.description == "Ключевая система"

    def test_name_unique(self):
        InformationSystemFactory(name="ERP")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                InformationSystemFactory(name="ERP")

    def test_str_returns_name(self):
        isys = InformationSystemFactory(name="Billing")
        assert str(isys) == "Billing"