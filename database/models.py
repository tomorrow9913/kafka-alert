from typing import List

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, ForeignKeyConstraint, Integer, JSON, PrimaryKeyConstraint, Sequence, SmallInteger, String, Table, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship
from sqlalchemy.orm.base import Mapped

from database.database import project_base

Base = project_base
metadata = Base.metadata


class ContainerLog(Base):
    __tablename__ = 'ContainerLog'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='ContainerLog_pkey'),
    )

    id = mapped_column(BigInteger, Sequence('ContainerLog_id_seq4'))
    systemcall = mapped_column(Integer)
    enter_or_exit = mapped_column(Boolean)
    container_name = mapped_column(String(255))
    pid = mapped_column(Integer)
    ppid = mapped_column(Integer)
    tid = mapped_column(Integer)
    uid = mapped_column(Integer)
    gid = mapped_column(Integer)
    command = mapped_column(String(64))
    atr_0 = mapped_column(String(255))
    atr_1 = mapped_column(String(255))
    atr_2 = mapped_column(String(255))
    atr_3 = mapped_column(String(255))
    atr_4 = mapped_column(String(255))
    atr_5 = mapped_column(String(255))
    return_value = mapped_column(BigInteger)
    additional_info = mapped_column(String(255))
    called_at = mapped_column(DateTime)
    created_at = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    mnt_namespace = mapped_column(BigInteger)
    pid_namespace = mapped_column(BigInteger)


class Heartbeat(Base):
    __tablename__ = 'Heartbeat'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='Heartbeat_pkey'),
    )

    id = mapped_column(BigInteger, Sequence('Heartbeat_id_seq1'))
    uuid = mapped_column(String(255), nullable=False)
    timestamp = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    survival_container_cnt = mapped_column(Integer, nullable=False, server_default=text('0'))
    req_ip = mapped_column(String(255), nullable=False)
    endpoint = mapped_column(String(255), nullable=False)

class LsmLog(Base):
    __tablename__ = 'LsmLog'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='LsmLog_pkey'),
    )

    insert_time = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    id = mapped_column(BigInteger)
    path = mapped_column(String(4096))
    source = mapped_column(String(4096))
    comm = mapped_column(String(100))
    pid = mapped_column(BigInteger)
    ppid = mapped_column(BigInteger)
    host_pid = mapped_column(BigInteger)
    host_ppid = mapped_column(BigInteger)
    uid = mapped_column(BigInteger)
    event_id = mapped_column(Integer)
    cgroup_id = mapped_column(BigInteger)
    mnt_ns = mapped_column(BigInteger)
    pid_ns = mapped_column(BigInteger)
    ret_val = mapped_column(Integer)
    timestamp = mapped_column(DateTime)

class Policy(Base):
    __tablename__ = 'Policy'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='Policy_pkey'),
        UniqueConstraint('name', name='Policy_name_key')
    )

    id = mapped_column(BigInteger, Sequence('Policy_id_seq1'))
    name = mapped_column(String(255), nullable=False)
    created_at = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    api_version = mapped_column(String(255), nullable=False)
    predefined = mapped_column(Boolean, nullable=False, server_default=text('false'))
    description = mapped_column(Text, nullable=False, server_default=text("''::text"))
    updated_at = mapped_column(DateTime(True))

    LsmFilePolicy: Mapped[List['LsmFilePolicy']] = relationship('LsmFilePolicy', uselist=True, back_populates='policy')
    LsmNetPolicy: Mapped[List['LsmNetPolicy']] = relationship('LsmNetPolicy', uselist=True, back_populates='policy')
    LsmProcPolicy: Mapped[List['LsmProcPolicy']] = relationship('LsmProcPolicy', uselist=True, back_populates='policy')
    RawTracePointPolicy: Mapped[List['RawTracePointPolicy']] = relationship('RawTracePointPolicy', uselist=True, back_populates='policy')
    TracepointPolicy: Mapped[List['TracepointPolicy']] = relationship('TracepointPolicy', uselist=True, back_populates='policy')
    PolicyContainer: Mapped[List['PolicyContainer']] = relationship('PolicyContainer', uselist=True, back_populates='policy')


class Server(Base):
    __tablename__ = 'Server'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='Server_pkey'),
        UniqueConstraint('uuid', name='Server_uuid_key')
    )

    id = mapped_column(BigInteger, Sequence('Server_id_seq1'))
    uuid = mapped_column(String(255), nullable=False)
    name = mapped_column(String(255), nullable=False)
    created_at = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))

    Container: Mapped[List['Container']] = relationship('Container', uselist=True, back_populates='Server_')
    SystemInfo: Mapped[List['SystemInfo']] = relationship('SystemInfo', uselist=True, back_populates='server')

class Tag(Base):
    __tablename__ = 'Tag'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='Tag_pkey'),
    )

    id = mapped_column(BigInteger, Sequence('Tag_id_seq1'))
    name = mapped_column(String(255), nullable=False)

    container: Mapped['Container'] = relationship('Container', secondary='ContainerTag', back_populates='tag')


class Container(Base):
    __tablename__ = 'Container'
    __table_args__ = (
        ForeignKeyConstraint(['host_server'], ['Server.id'], name='FK__Server'),
        PrimaryKeyConstraint('id', name='Container_pkey'),
        UniqueConstraint('host_server', 'name', name='Container_host_server_name_key')
    )

    host_server = mapped_column(BigInteger, nullable=False)
    runtime = mapped_column(String(100), nullable=False)
    name = mapped_column(String(255), nullable=False)
    created_at = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    id = mapped_column(BigInteger, Sequence('Container_id_seq1'))
    removed_at = mapped_column(DateTime(True))

    Server_: Mapped['Server'] = relationship('Server', back_populates='Container')
    tag: Mapped['Tag'] = relationship('Tag', secondary='ContainerTag', back_populates='container')
    InternalContainerId: Mapped[List['InternalContainerId']] = relationship('InternalContainerId', uselist=True, back_populates='container')
    PolicyContainer: Mapped[List['PolicyContainer']] = relationship('PolicyContainer', uselist=True, back_populates='container')
    ContainerSysInfo: Mapped[List['ContainerSysInfo']] = relationship('ContainerSysInfo', uselist=True, back_populates='container')

class LsmFilePolicy(Base):
    __tablename__ = 'LsmFilePolicy'
    __table_args__ = (
        ForeignKeyConstraint(['policy_id'], ['Policy.id'], name='FK__Policy'),
        PrimaryKeyConstraint('id', name='LsmFilePolicy_pkey')
    )

    id = mapped_column(BigInteger, Sequence('LsmFilePolicy_id_seq1'))
    policy_id = mapped_column(BigInteger, nullable=False)
    path = mapped_column(String(4096), nullable=False)
    flags = mapped_column(JSON, nullable=False)
    uid = mapped_column(JSON, nullable=False)

    policy: Mapped['Policy'] = relationship('Policy', back_populates='LsmFilePolicy')


class LsmNetPolicy(Base):
    __tablename__ = 'LsmNetPolicy'
    __table_args__ = (
        ForeignKeyConstraint(['policy_id'], ['Policy.id'], name='FK__Policy'),
        PrimaryKeyConstraint('id', name='LsmNetPolicy_pkey')
    )

    id = mapped_column(BigInteger, Sequence('LsmNetPolicy_id_seq1'))
    policy_id = mapped_column(BigInteger, nullable=False)
    ip = mapped_column(String(256), nullable=False)
    port = mapped_column(Integer, nullable=False)
    protocol = mapped_column(SmallInteger, nullable=False)
    flags = mapped_column(JSON, nullable=False)
    uid = mapped_column(JSON, nullable=False)

    policy: Mapped['Policy'] = relationship('Policy', back_populates='LsmNetPolicy')


class LsmProcPolicy(Base):
    __tablename__ = 'LsmProcPolicy'
    __table_args__ = (
        ForeignKeyConstraint(['policy_id'], ['Policy.id'], name='FK__Policy'),
        PrimaryKeyConstraint('id', name='LsmProcPolicy_pkey')
    )

    id = mapped_column(BigInteger, Sequence('LsmProcPolicy_id_seq1'))
    policy_id = mapped_column(BigInteger, nullable=False)
    comm = mapped_column(String(16), nullable=False)
    flags = mapped_column(JSON, nullable=False)
    uid = mapped_column(JSON, nullable=False)

    policy: Mapped['Policy'] = relationship('Policy', back_populates='LsmProcPolicy')


class RawTracePointPolicy(Base):
    __tablename__ = 'RawTracePointPolicy'
    __table_args__ = (
        ForeignKeyConstraint(['policy_id'], ['Policy.id'], name='FK__Policy'),
        PrimaryKeyConstraint('id', name='RawTracePointPolicy_pkey')
    )

    id = mapped_column(BigInteger, Sequence('RawTracePointPolicy_id_seq1'))
    policy_id = mapped_column(BigInteger, nullable=False)
    state = mapped_column(Boolean, nullable=False)

    policy: Mapped['Policy'] = relationship('Policy', back_populates='RawTracePointPolicy')


class TracepointPolicy(Base):
    __tablename__ = 'TracepointPolicy'
    __table_args__ = (
        ForeignKeyConstraint(['policy_id'], ['Policy.id'], name='FK_TracepointPolicy_Policy'),
        PrimaryKeyConstraint('id', name='TracepointPolicy_pkey')
    )

    id = mapped_column(BigInteger, Sequence('TracepointPolicy_id_seq1'))
    policy_id = mapped_column(BigInteger, nullable=False)
    tracepoint = mapped_column(String(100), nullable=False)

    policy: Mapped['Policy'] = relationship('Policy', back_populates='TracepointPolicy')


class ContainerSysInfo(Base):
    __tablename__ = 'ContainerSysInfo'
    __table_args__ = (
        ForeignKeyConstraint(['container_id'], ['Container.id'], name='FK_ContainerSysInfo_Container'),
        PrimaryKeyConstraint('container_id', 'timestamp', name='ContainerSysInfo_pkey')
    )

    container_id = mapped_column(BigInteger, nullable=False)
    cpu_kernel = mapped_column(Float, nullable=False)
    cpu_user = mapped_column(Float, nullable=False)
    cpu_percent = mapped_column(Float, nullable=False)
    cpu_online = mapped_column(Float, nullable=False)
    disk_read_mb = mapped_column(Float, nullable=False)
    disk_write_mb = mapped_column(Float, nullable=False)
    mem_limit = mapped_column(Float, nullable=False)
    mem_usage = mapped_column(Float, nullable=False)
    mem_percent = mapped_column(Float, nullable=False)
    net_recv_mb = mapped_column(Float, nullable=False)
    net_send_mb = mapped_column(Float, nullable=False)
    net_recv_packets = mapped_column(Integer, nullable=False)
    net_send_packets = mapped_column(Integer, nullable=False)
    proc_cnt = mapped_column(Integer, nullable=False)
    timestamp = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    ip = mapped_column(String(255), nullable=False)

    container: Mapped['Container'] = relationship('Container', back_populates='ContainerSysInfo')


class ContainerTag(Base):
    __tablename__ = 'ContainerTag'
    __table_args__ = (
        ForeignKeyConstraint(['container_id'], ['Container.id'], name='FK__Container'),
        ForeignKeyConstraint(['tag_id'], ['Tag.id'], name='FK__Tag'),
        PrimaryKeyConstraint('container_id', 'tag_id', name='ContainerTag_pkey')
    )

    container_id = mapped_column(BigInteger, nullable=False, primary_key=True)
    tag_id = mapped_column(BigInteger, nullable=False, primary_key=True)


class InternalContainerId(Base):
    __tablename__ = 'InternalContainerId'
    __table_args__ = (
        ForeignKeyConstraint(['container_idx'], ['Container.id'], name='FK_InternalContainerId_Container'),
        PrimaryKeyConstraint('id', name='InternalContainerId_pkey'),
        UniqueConstraint('container_idx', 'pid_id', 'mnt_id', 'cgroup_id', name='InternalContainerId_container_id_pid_id_mnt_id_cgroup_id_key')
    )

    id = mapped_column(BigInteger, Sequence('InternalContainerId_id_seq2'))
    container_idx = mapped_column(BigInteger, nullable=False)
    pid_id = mapped_column(BigInteger, nullable=False)
    mnt_id = mapped_column(BigInteger, nullable=False)
    cgroup_id = mapped_column(BigInteger, nullable=False)
    reg_time = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    image = mapped_column(String(255), nullable=False)
    container_id = mapped_column(String(64), nullable=False)

    container: Mapped['Container'] = relationship('Container', back_populates='InternalContainerId')


class PolicyContainer(Base):
    __tablename__ = 'PolicyContainer'
    __table_args__ = (
        ForeignKeyConstraint(['container_id'], ['Container.id'], name='FK_PolicyContainer_Container'),
        ForeignKeyConstraint(['policy_id'], ['Policy.id'], name='FK_PolicyContainer_Policy'),
        PrimaryKeyConstraint('id', name='PolicyContainer_pkey')
    )

    id = mapped_column(BigInteger)
    policy_id = mapped_column(BigInteger, nullable=False)
    container_id = mapped_column(BigInteger, nullable=False)

    container: Mapped['Container'] = relationship('Container', back_populates='PolicyContainer')
    policy: Mapped['Policy'] = relationship('Policy', back_populates='PolicyContainer')
    
class SystemInfo(Base):
    __tablename__ = 'SystemInfo'
    __table_args__ = (
        ForeignKeyConstraint(['server_id'], ['Server.id'], name='FK_SystemInfo_Server'),
        PrimaryKeyConstraint('server_id', 'timestamp', name='SystemInfo_pkey')
    )

    server_id = mapped_column(BigInteger, nullable=False)
    cpu_logic_core = mapped_column(SmallInteger, nullable=False)
    cpu_physic_core = mapped_column(SmallInteger, nullable=False)
    cpu_percent = mapped_column(Float, nullable=False)
    cpu_core_usage = mapped_column(JSON, nullable=False)
    mem_total = mapped_column(Float, nullable=False)
    mem_used = mapped_column(Float, nullable=False)
    mem_percent = mapped_column(Float, nullable=False)
    disk_read_mb = mapped_column(Float, nullable=False)
    disk_write_mb = mapped_column(Float, nullable=False)
    disk_total = mapped_column(Float, nullable=False)
    disk_used = mapped_column(Float, nullable=False)
    disk_percent = mapped_column(Float, nullable=False)
    net_recv_data_mb = mapped_column(Float, nullable=False)
    net_send_data_mb = mapped_column(Float, nullable=False)
    net_recv_packets = mapped_column(Integer, nullable=False)
    net_send_packets = mapped_column(Integer, nullable=False)
    net_recv_err = mapped_column(Integer, nullable=False)
    net_send_err = mapped_column(Integer, nullable=False)
    uptime = mapped_column(Float, nullable=False)
    load_avg = mapped_column(JSON, nullable=False)
    timestamp = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))

    server: Mapped['Server'] = relationship('Server', back_populates='SystemInfo')
