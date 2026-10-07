# ==============================================================================
# 3. Google Cloud Model Armor Template (`fsi-agent-armor-strict`)
# ==============================================================================

resource "terraform_data" "model_armor_template_fsi_strict" {
  triggers_replace = [
    var.project_id,
    var.region,
    var.model_armor_template_id,
  ]

  provisioner "local-exec" {
    command = <<-EOT
      TOKEN=$(gcloud auth print-access-token)
      BASE_URL="https://modelarmor.${var.region}.rep.googleapis.com/v1/projects/${var.project_id}/locations/${var.region}/templates"
      PAYLOAD='{
        "filterConfig": {
          "piAndJailbreakFilterSettings": {
            "filterEnforcement": "ENABLED",
            "confidenceLevel": "LOW_AND_ABOVE"
          },
          "maliciousUriFilterSettings": {
            "filterEnforcement": "ENABLED"
          },
          "sdpSettings": {
            "basicConfig": {
              "filterEnforcement": "ENABLED"
            }
          },
          "raiSettings": {
            "raiFilters": [
              {"filterType": "HATE_SPEECH", "confidenceLevel": "MEDIUM_AND_ABOVE"},
              {"filterType": "DANGEROUS", "confidenceLevel": "LOW_AND_ABOVE"},
              {"filterType": "HARASSMENT", "confidenceLevel": "MEDIUM_AND_ABOVE"},
              {"filterType": "SEXUALLY_EXPLICIT", "confidenceLevel": "MEDIUM_AND_ABOVE"}
            ]
          }
        },
        "templateMetadata": {
          "multiLanguageDetection": {"enableMultiLanguageDetection": true},
          "logTemplateOperations": true,
          "logSanitizeOperations": true
        },
        "labels": {
          "datacloud": "jetski",
          "vertical": "financial-services",
          "gateway": "apigee-x"
        }
      }'
      STATUS=$(curl -s -o /dev/null -w "%%{http_code}" -X POST "$${BASE_URL}?templateId=${var.model_armor_template_id}" \
        -H "Authorization: Bearer $${TOKEN}" \
        -H "X-Goog-User-Project: ${var.project_id}" \
        -H "Content-Type: application/json" \
        -d "$${PAYLOAD}")
      if [ "$${STATUS}" = "409" ]; then
        curl -s -X PATCH "$${BASE_URL}/${var.model_armor_template_id}" \
          -H "Authorization: Bearer $${TOKEN}" \
          -H "X-Goog-User-Project: ${var.project_id}" \
          -H "Content-Type: application/json" \
          -d "$${PAYLOAD}"
      fi
    EOT
  }

  depends_on = [google_project_service.enabled_apis]
}
