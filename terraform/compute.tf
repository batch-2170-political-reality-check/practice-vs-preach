# Enable required APIs
resource "google_project_service" "compute" {
  project            = data.google_project.project.project_id
  service            = "compute.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "vpcaccess" {
  project            = data.google_project.project.project_id
  service            = "vpcaccess.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "iap" {
  project            = data.google_project.project.project_id
  service            = "iap.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "networkmanagement" {
  project            = data.google_project.project.project_id
  service            = "networkmanagement.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "monitoring" {
  project            = data.google_project.project.project_id
  service            = "monitoring.googleapis.com"
  disable_on_destroy = false
}

# VPC Network (or use default)
resource "google_compute_network" "vpc" {
  name                    = "project-vpc"
  auto_create_subnetworks = false
  project                 = data.google_project.project.project_id
}

resource "google_compute_subnetwork" "subnet" {
  name          = "project-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = local.location
  network       = google_compute_network.vpc.id
  project       = data.google_project.project.project_id
}

# Cloud Router for NAT
resource "google_compute_router" "router" {
  name    = "project-router"
  region  = local.location
  network = google_compute_network.vpc.id
  project = data.google_project.project.project_id
}

# Cloud NAT for outbound internet access
resource "google_compute_router_nat" "nat" {
  name    = "project-nat"
  router  = google_compute_router.router.name
  region  = local.location
  project = data.google_project.project.project_id

  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Serverless VPC Access Connector (for Cloud Run to reach VM)
resource "google_vpc_access_connector" "connector" {
  name          = "project-connector"
  region        = local.location
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.8.0.0/28" # Must be /28 and not overlap with subnet
  project       = data.google_project.project.project_id
  min_instances = 2
  max_instances = 3
}

# Firewall rule to allow Cloud Run -> ChromaDB
resource "google_compute_firewall" "chromadb_internal" {
  name    = "allow-chromadb-internal"
  network = google_compute_network.vpc.name
  project = data.google_project.project.project_id

  allow {
    protocol = "tcp"
    ports    = ["8000"]
  }

  # Allow from VPC connector range
  source_ranges = ["10.8.0.0/28"]
  target_tags   = ["chromadb"]
}

# Firewall rule to allow SSH via IAP
resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "allow-iap-ssh"
  network = google_compute_network.vpc.name
  project = data.google_project.project.project_id

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  # IAP's IP range for SSH tunneling
  source_ranges = ["35.235.240.0/20"]
}

# Persistent disk for ChromaDB data
resource "google_compute_disk" "chromadb_data" {
  name    = "chromadb-data"
  type    = "pd-standard" # or pd-ssd for better performance
  zone    = "${local.location}-a"
  size    = 20 # GB - adjust based on your needs
  project = data.google_project.project.project_id
}

# ChromaDB VM Instance
#
# $(gcloud info --format="value(basic.python_location)") -m pip install numpy
# gcloud compute ssh chromadb-vm --zone=europe-west10-a --tunnel-through-iap # --troubleshoot
# curl http://localhost:8000/api/v1/heartbeat
# curl http://localhost:8000/api/v2/tenants/default_tenant/databases/default_database/collections
resource "google_compute_instance" "chromadb" {
  name         = "chromadb-vm"
  machine_type = "e2-small" # 2 vCPU, 2GB RAM - adjust as needed
  zone         = "${local.location}-a"
  project      = data.google_project.project.project_id

  tags = ["chromadb"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
      size  = 10 # GB for OS
    }
  }

  attached_disk {
    source      = google_compute_disk.chromadb_data.self_link
    device_name = "chromadb-data"
  }

  network_interface {
    network    = google_compute_network.vpc.name
    subnetwork = google_compute_subnetwork.subnet.name

    # No external IP - internal only
    # Uncomment if you need external access for debugging:
    # access_config {}
  }

  service_account {
    email  = google_service_account.project_sa.email
    scopes = ["cloud-platform"]
  }

  metadata_startup_script = templatefile("${path.module}/files/chromadb-startup.sh", {
    disk_device = "/dev/disk/by-id/google-chromadb-data"
  })

  # Ensure disk exists first
  depends_on = [google_compute_disk.chromadb_data]
}

# Output the internal IP
output "chromadb_internal_ip" {
  value       = google_compute_instance.chromadb.network_interface[0].network_ip
  description = "Internal IP address of ChromaDB VM"
}

output "vpc_connector_name" {
  value       = google_vpc_access_connector.connector.name
  description = "VPC connector name for Cloud Run"
}
