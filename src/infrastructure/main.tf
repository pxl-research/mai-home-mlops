# Configure the Microsoft Azure provider
provider "azurerm" {
    features {}
}

# Create a Resource Group if it doesn’t exist
resource "azurerm_resource_group" "mai_home_mlops_rg" {
    name     = "mai-home-rg"
    location = "West Europe"
}