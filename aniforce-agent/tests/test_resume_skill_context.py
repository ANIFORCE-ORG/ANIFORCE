from app.runtime.resume_executor import extract_checkpoint_workspace_context


def test_extracts_workspace_context_from_sdk_context_wrapper():
    run_state = {
        "context": {
            "value": {
                "usage": {"requests": 2},
                "approvals": {},
                "context": {
                    "user_id": "u1",
                    "selected_skill_ids": ["safe_business_mutation"],
                    "selected_skill_versions": {"safe_business_mutation": "1.0"},
                    "skill_slots": {"operation": "create"},
                    "skill_status": "ready",
                },
            }
        }
    }
    extracted = extract_checkpoint_workspace_context(run_state)
    assert extracted["user_id"] == "u1"
    assert extracted["selected_skill_ids"] == ["safe_business_mutation"]
    assert extracted["skill_slots"] == {"operation": "create"}


def test_extracts_current_sdk_direct_wrapper_shape():
    current = {
        "context": {
            "usage": {"requests": 2},
            "context": {
                "user_id": "u1",
                "selected_skill_ids": ["safe_business_mutation"],
            },
        }
    }
    assert extract_checkpoint_workspace_context(current) == {
        "user_id": "u1",
        "selected_skill_ids": ["safe_business_mutation"],
    }


def test_accepts_legacy_direct_context_shape():
    direct = {"context": {"value": {"user_id": "u1", "task_type": "conversation"}}}
    assert extract_checkpoint_workspace_context(direct) == {
        "user_id": "u1",
        "task_type": "conversation",
    }
