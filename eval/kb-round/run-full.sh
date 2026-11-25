#!/usr/bin/env bash
# the published KB round: the whole of family-readmes-v1, fresh build, default judge
cd ~/dsh-auto-ontology && . /tmp/o5/e2/kb/env.sh
echo "START $(date '+%F %T %Z')"
ONTOLOGY_HOME=/tmp/o5/e2/kb/ontologies python3 scripts/build_ontology.py \
  --kb 035be669-f79c-458f-b119-f295d1e65859 \
  --domain "$(cat /tmp/o5/e2/kb/domain.txt)" --save
echo "EXIT $? $(date '+%F %T %Z')"
