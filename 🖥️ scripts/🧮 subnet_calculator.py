import math
import ipaddress
import subprocess

lans = {
    "Rectoria": 10,
    "Administrativos": 31,
    "Profesores": 200,
    "Estudiantes": 100,
    "InvitadosWLAN": 50,
    "GestionTIC": 20,
    "Primaria": 50,
    "Secundaria_XX": 10,
    "Profesores_XX": 99,
    "Estudiantes_XX": 199,
    "InvitadosWLAN_XX": 200,
    "GestionTIC_XX": 20,
    "Secundaria_YY": 70,
    "Media_YY": 20,
    "Profesores_YY": 99,
    "Estudiantes_YY": 299,
    "InvitadosWLAN_YY": 100,
    "GestionTIC_YY": 30,
    "Secundaria_ZZ": 20,
    "Media_ZZ": 50,
    "Profesores_ZZ": 99,
    "Estudiantes_ZZ": 199,
    "InvitadosWLAN_ZZ": 40,
    "GestionTIC_ZZ": 20,
    "Servidores_ZZ": 5
}


def calcular_subredes(lans):
    resultados = []
    for lan, hosts in lans.items():
        nuevos_hosts = math.ceil(hosts * 1.1)  # Add 10% margin
        hosts_requeridos = nuevos_hosts + 2
        bits_mascara = 32 - math.ceil(math.log2(hosts_requeridos))
        resultados.append((lan, nuevos_hosts, f"/{bits_mascara}"))
    return resultados


resultados_subredes = calcular_subredes(lans)

# Base network
YY = 50
red_base = ipaddress.IPv4Address(f"10.{YY}.0.0")

# Sort subnets by mask size (largest to smallest)
subredes_ordenadas = sorted(
    resultados_subredes,
    key=lambda x: int(x[2][1:]),
    reverse=False
)

# Assign subnets
subredes_asignadas = []
ip_actual = red_base  # Base IP
print(f"IP Base: {ip_actual}")


def siguiente_subred(ip, cidr):
    """Calculate the next subnet, given the CIDR mask."""
    incremento = 2**(32 - int(cidr))
    nuevo_ip = int(ip) + incremento
    return ipaddress.IPv4Address(nuevo_ip)


for lan, hosts, cidr in subredes_ordenadas:
    subred = ipaddress.IPv4Network(f"{ip_actual}{cidr}", strict=False)
    subredes_asignadas.append((lan, subred))
    ip_actual = siguiente_subred(subred.network_address, cidr[1:])


def ips_hosts(subred, num_hosts):
    hosts = []
    for i, ip in enumerate(subred.hosts()):
        if i >= num_hosts:
            break
        hosts.append(str(ip))
    return hosts


ips_asignadas = []
for idx, (lan, subred) in enumerate(subredes_asignadas):
    ip_iter = subred.hosts()
    ip_router = str(next(ip_iter))
    ip_switch = str(next(ip_iter))
    hosts = ips_hosts(subred, lans[lan])

    interfaz_router = f"eth{2*idx}"
    interfaz_switch = f"eth{2*idx+1}"

    interfaces_permitidas = {'eth0', 'eth1', 'eth2'}  # Update as necessary
    if (interfaz_router not in interfaces_permitidas or
            interfaz_switch not in interfaces_permitidas):
        raise ValueError(
            f"One or both interfaces '{interfaz_router}',"
            f"'{interfaz_switch}' are not permitted."
        )

    try:
        subprocess.run(
            [
                '/usr/sbin/ip', 'addr', 'add',
                f'{ip_router}/{subred.prefixlen}', 'dev', interfaz_router
            ],
            check=True
        )
        subprocess.run(
            ['/usr/sbin/ip', 'link', 'set', interfaz_router, 'up'],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Failed to configure router interface {interfaz_router}: {e}")

    # Configure switch interface
    try:
        subprocess.run(
            [
                '/usr/sbin/ip', 'addr', 'add',
                f'{ip_switch}/{subred.prefixlen}', 'dev', interfaz_switch
            ],
            check=True
        )
        subprocess.run(
            ['/usr/sbin/ip', 'link', 'set', interfaz_switch, 'up'],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Failed to configure switch interface {interfaz_switch}: {e}")

    ips_asignadas.append({
        "LAN": lan,
        "Subred": str(subred),
        "IP Router": ip_router,
        "IP Switch": ip_switch,
    })
