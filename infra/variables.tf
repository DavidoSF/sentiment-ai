variable "image_tag" {
  description = " Tag de l'image Docker a deployer "
  type        = string
  default     = "latest"
}
# Port 8080 reserve a Jenkins -- staging sur 8001
variable "app_port" {
  description = " Port expose en staging "
  type        = number
  default     = 8001
}
variable "container_name" {
  description = " Nom du conteneur staging "
  type        = string
  default     = "sentiment-staging"
}
variable "registry" {
  description = " Registry Docker (ex: ghcr .io/ monpseudo )"
  type        = string
  default     = " ghcr.io/DavidoSF"
}