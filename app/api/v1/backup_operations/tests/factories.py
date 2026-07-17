import factory
from django.utils import timezone
from systems.models import TargetSystem, TargetSystemVersion
from dictionaries.models import SystemType, Environment, BackupTool, InformationSystem
from configurations.models import BackupConfiguration, BackupConfigurationVersion
from operations.models import BackupOperation


class SystemTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SystemType
    name = factory.Sequence(lambda n: f'type_{n}')


class EnvironmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Environment
    name = factory.Sequence(lambda n: f'env_{n}')


class BackupToolFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BackupTool
    name = factory.Sequence(lambda n: f'tool_{n}')
    is_active = True

class InformationSystemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InformationSystem
    name = factory.Sequence(lambda n: f'is_{n}')

class TargetSystemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TargetSystem
    system_type = factory.SubFactory(SystemTypeFactory)
    environment = factory.SubFactory(EnvironmentFactory)
    name = factory.Sequence(lambda n: f'system_{n}')
    is_active = True


class TargetSystemVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TargetSystemVersion
    target_system = factory.SubFactory(TargetSystemFactory)
    version_number = 1
    is_current = True
    valid_from = factory.LazyFunction(timezone.now)


class BackupConfigurationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BackupConfiguration
    target_system_version = factory.SubFactory(TargetSystemVersionFactory)
    name = factory.Sequence(lambda n: f'config_{n}')
    is_active = True


class BackupConfigurationVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BackupConfigurationVersion
    backup_configuration = factory.SubFactory(BackupConfigurationFactory)
    backup_tool = factory.SubFactory(BackupToolFactory)
    version_number = 1
    is_current = True
    valid_from = factory.LazyFunction(timezone.now)


class BackupOperationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BackupOperation
    backup_configuration_version = factory.SubFactory(BackupConfigurationVersionFactory)
    hostname = 'test-host'
    status = 'in_progress'