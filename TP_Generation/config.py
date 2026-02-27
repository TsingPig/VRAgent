TEST_PLAN_NO_TODG_REQUEST_TEMPLATE = """Imagine you are helping software test engineers to create comprehensive test plans without delving into the specifics of the code. Test engineers want to test the {app_name} App. One game object we want to test is in the scene of '{scene_name}.unity'.
Despite the events that can be triggered automatically, please choose the event we want to trigger in some conditions. We will provide the source code of the script attached to this gameobjects below. There may be more than one script attached to one gameobject. And the scene meta setting (MonoBehaviour Component) is shown corresponding to the script file shown.
[Source code of script files attached]
'''
{script_source}
'''
[Extracted JSON format of scene meta file] The scene file of '{scene_name}.unity' can specify the detailed settings of gameobjects and its attached Monobehavior. Please specify that the Monobehaviour component in the scene file I provided is the exact settings of the script file attached to the game objects we want to test. Please notice that the 'm_Calls' in MonoBehaviour component are the Interactable events that also need to be triggered manually or automatically to test the scripts. Please read the file below.
'''
{scene_meta}
'''
[Format of Test Plans] The test plan should contain actions chosen from the action list: ['Grab', 'Trigger', 'Transform']. You should choose these actions according to the related information of the target gameobject you want to interact with. Use 'm_PrefabInstance' fileID as the target GameObject's 'source_object_fileID' if it has 'PrefabInstance' component. In their attached scripts, there may be interfaces or APIs to indicate that you can only interact with these gameobjects using specific action. Also, if the target GameObject is called "Player" or "player", please do not choose 'Grab' and 'Transform' actions. Also, do not directly perform actions on the controllers that may derive from XR Interaction Toolkit, also do not directly perform actions on our test agent. \n\nPlease structure your response in the following JSON format:
'''
{{
  "taskUnits": [
    {{
      "actionUnits": [
        {{
          "type": "Grab",
          "source_object_name": {{source_object_name}},
          "source_object_fileID": {{source_object_fileID}},
          "target_object_name": {{target_object_name}},
          "target_object_fileID": {{target_object_fileID}}
        }}
      ]
    }},
    {{
      "actionUnits": [
        {{
          "type": "Trigger",
          "source_object_name": {{source_object_name}},
          "triggerring_time": {{triggerring_time}},
          "source_object_fileID": {{source_object_fileID}},
          "condition": "Trigger condition description (may include script ID, GUID, serialization config, expected behavior calls)",
          "triggerring_events": [
            {{
              "methodCallUnits": [
                {{
                  "script_fileID": {{script_fileID}},
                  "method_name": {{method_name}},
                  "parameter_fileID": [{{parameter_fileID}}]
                }}
              ]
            }}
          ]
        }}
      ]
    }},
    {{
      "actionUnits": [
        {{
          "type": "Transform",
          "source_object_name": {{source_object_name}},
          "source_object_fileID": {{source_object_fileID}},
          "delta_position": {{
            "x": {{x}},
            "y": {{y}},
            "z": {{z}}
          }},
          "delta_rotation": {{
            "x": {{x}},
            "y": {{y}},
            "z": {{z}}
          }},
          "delta_scale": {{
            "x": {{x}},
            "y": {{y}},
            "z": {{z}}
          }},
          "triggerring_events": [
            {{
              "methodCallUnits": [
                {{
                  "script_fileID": {{script_fileID}},
                  "method_name": {{method_name}},
                  "parameter_fileID": [{{parameter_fileID}}]
                }}
              ]
            }}
          ],
          "triggerred_events": [
          ],
          "triggerring_time": {{triggerring_time}}
          }}
      ]
    }}
  ],
  "Need_more_Info": true/false
}}
'''
**Action Type Guidelines:**
- **Grab**: Grab or pick up source object and drop it to the target object or position.
Grab action format1:
{{
  "type": "Grab",
  "source_object_name": "<string>",       // Name of the agent or object initiating the grab
  "source_object_fileID": <long>,         // FileID of the source object in the Unity scene file
  "target_object_name": "<string>",       // Name of the target object being grabbed
  "target_object_fileID": <long>          // FileID of the target object in the Unity scene file
}}
Grab action format2:
{{
  "type": "Grab",
  "source_object_name": "<string>",       // Name of the source object
  "source_object_fileID": <long>,         // FileID of the source object in the Unity scene file
  "target_position": {{                    // Target world position to which the object should be moved
    "x": "<float>",
    "y": "<float>",
    "z": "<float>"
  }}
}}
- **Trigger**: Trigger describes the triggering process in interactive actions, mainly used to simulate the player's interaction with objects in VR scenes, such as clicking a button, pulling a lever, or triggering a state change. 'Trigger' action can only support to trigger public methods that inherit from MonoBehaviour with no parameters of script file.
Trigger action format:
{{
  "type": "Trigger",
  "source_object_name": "<string>",       // Name of the source object that triggers the event
  "triggerring_time": <float>, 			      // Duration of the trigger
  "source_object_fileID": <long>,         // FileID of the source object in Unity scene file
  "condition": "<string>",                // Trigger condition description (may include script ID, GUID, serialization config, expected behavior calls)
  "triggerring_events": [                 // List of events during the Trigger process, these events will be triggered witin one frame.
    // 0 or more event units
    {{
      "methodCallUnits": [                // An event unit containing 0 or more methodCallUnit
        {{
          "script_fileID": <long>,       // FileID of the target MonoBehaviour Component
          "method_name": "<string>",     // Name of public method with no parameters to call
          "parameter_fileID": []         // No need to fill. Must be empty.
        }}
      ]
    }}
  ],
  "triggerred_events": [                  // List of events after 'triggering_events' have completed, 'triggerred_events' will be executed after waiting for the triggering time. These events will also be triggered within one frame.
    	// 0 or more event units
  ]
}}
- **Transform**: A Transform describes translation, rotation, and scale operations on an object, used to implement incremental adjustments (delta) of object states within an action unit. It can support to execute 'Trigger' action simultaneously.
Transform action format:
{{
  "type": "Transform",
  "source_object_name": "<string>",        // Target object name
  "source_object_fileID": <long>,          // FileID of the object in Unity scene
  "delta_position": {{                     // Position delta (offset)
    "x": <float>,
    "y": <float>,
    "z": <float>
  }},
  "delta_rotation": {{                     // Rotation delta (offset)
    "x": <float>,
    "y": <float>,
    "z": <float>
  }},
  "delta_scale": {{                        // Scale delta (offset)
    "x": <float>,
    "y": <float>,
    "z": <float>
  }},
  "triggerring_events": [                 // List of events during the Trigger process, these events will be triggered witin one frame.
        // 0 or more event units
        {{
          "methodCallUnits": [                // An event unit containing 0 or more methodCallUnit
            {{
              "script_fileID": <long>,     // FileID of the target MonoBehaviour Component
              "method_name": "<string>",     // Name of public method with no parameters to call
              "parameter_fileID": []         // No need to fill. Must be empty.
            }}
          ]
        }}
      ],
  "triggerred_events": [                  // List of events after 'triggering_events' have completed, 'triggerred_events' will be executed after waiting for the triggering time. These events will also be triggered within one frame.
            // 0 or more event units
      ],
  "triggerring_time": <float>                  // Duration of the action
}}
**Redundancy Avoidance Policy:**
- If you choose to add a "Trigger" action, please first check if the event will already be triggered naturally by a previous actions. If so, you don't need to add manual "Trigger" actions.
- Please try to avoid adding manual "Trigger" actions. Please wait until we provide you with all the children information to choose 'Trigger' action.
- For scene meta settings on 'm_Calls', you are encouraged to add 'Trigger' action to trigger the event in case that it cannot be triggered automatically.

Please respond with the test plan for this gameobject.
"""

# Test Plan Generation Prompt Templates
TEST_PLAN_FIRST_REQUEST_TEMPLATE = """Imagine you are helping software test engineers to create comprehensive test plans without delving into the specifics of the code. Test engineers want to test the {app_name} App. One game object we want to test in the scene of '{scene_name}.unity' is '{gobj_name}'.
Despite the events that can be triggered automatically, please choose the event we want to trigger in some conditions. We will provide the source code attached to this gameobjects below.
[Extracted JSON format of scene meta file] The scene file of '{scene_name}.unity' can specify the detailed settings of gameobjects and its attached Monobehavior. I'll provide you with the related information of game object '{gobj_name}' and its script. The 'fileID' of gameobject '{gobj_name}' is: {gobj_id}. Please specify that the Monobehaviour component in the scene file I provided is the exact settings of the script file attached to the game objects we want to test. Please notice that the 'm_Calls' in MonoBehaviour component are the Interactable events that also need to be triggered manually or automatically to test the scripts. And the Collider component defines the shape of a GameObject for the purpose of physical collisions. 'Has_Rigidbody' indicates whether the gameobject has Rigidbody component. 'Has_Event_Trigger' indicates the gameobject has EventTrigger MonoBehaviour component. Please read the file below.
'''
{scene_meta}
'''
[Format of Test Plans] The test plan should contain actions chosen from the action list: ['Grab', 'Trigger', 'Transform']. You should choose these actions according to the related information of the target gameobject you want to interact with. Use 'm_PrefabInstance' fileID as the target GameObject's 'source_object_fileID' if it has 'PrefabInstance' component. Please remind that 'Grab' and 'Transform' can only interact with gameobjects that have Rigidbody component. 'Trigger' action can only interact with gameobjects that have Rigidbody or Collider or EventTrigger component, or their attached script has class inherit from UnityEngine.Events. In their attached scripts, there may be interfaces or APIs to indicate that you can only interact with these gameobjects using specific action. Also, if the target GameObject is called "Player" or "player", please do not choose 'Grab' and 'Transform' actions. Also, do not directly perform actions on the controllers that may derive from XR Interaction Toolkit, also do not directly perform actions on our test agent. \n\nPlease structure your response in the following JSON format:
'''
{{
  "taskUnits": [
    {{
      "actionUnits": [
        {{
          "type": "Grab",
          "source_object_name": {{source_object_name}},
          "source_object_fileID": {{source_object_fileID}},
          "target_object_name": {{target_object_name}},
          "target_object_fileID": {{target_object_fileID}}
        }}
      ]
    }},
    {{
      "actionUnits": [
        {{
          "type": "Trigger",
          "source_object_name": {{source_object_name}},
          "triggerring_time": {{triggerring_time}},
          "source_object_fileID": {{source_object_fileID}},
          "condition": "Trigger condition description (may include script ID, GUID, serialization config, expected behavior calls)",
          "triggerring_events": [
            {{
              "methodCallUnits": [
                {{
                  "script_fileID": {{script_fileID}},
                  "method_name": {{method_name}},
                  "parameter_fileID": [{{parameter_fileID}}]
                }}
              ]
            }}
          ]
        }}
      ]
    }},
    {{
      "actionUnits": [
        {{
          "type": "Transform",
          "source_object_name": {{source_object_name}},
          "source_object_fileID": {{source_object_fileID}},
          "delta_position": {{
            "x": {{x}},
            "y": {{y}},
            "z": {{z}}
          }},
          "delta_rotation": {{
            "x": {{x}},
            "y": {{y}},
            "z": {{z}}
          }},
          "delta_scale": {{
            "x": {{x}},
            "y": {{y}},
            "z": {{z}}
          }},
          "triggerring_events": [
            {{
              "methodCallUnits": [
                {{
                  "script_fileID": {{script_fileID}},
                  "method_name": {{method_name}},
                  "parameter_fileID": [{{parameter_fileID}}]
                }}
              ]
            }}
          ],
          "triggerred_events": [
          ],
          "triggerring_time": {{triggerring_time}}
          }}
      ]
    }}
  ],
  "Need_more_Info": true/false
}}
'''
**Action Type Guidelines:**
- **Grab**: Grab or pick up source object and drop it to the target object or position.
Grab action format1:
{{
  "type": "Grab",
  "source_object_name": "<string>",       // Name of the agent or object initiating the grab
  "source_object_fileID": <long>,         // FileID of the source object in the Unity scene file
  "target_object_name": "<string>",       // Name of the target object being grabbed
  "target_object_fileID": <long>          // FileID of the target object in the Unity scene file
}}
Grab action format2:
{{
  "type": "Grab",
  "source_object_name": "<string>",       // Name of the source object
  "source_object_fileID": <long>,         // FileID of the source object in the Unity scene file
  "target_position": {{                    // Target world position to which the object should be moved
    "x": "<float>",
    "y": "<float>",
    "z": "<float>"
  }}
}}
- **Trigger**: Trigger describes the triggering process in interactive actions, mainly used to simulate the player's interaction with objects in VR scenes, such as clicking a button, pulling a lever, or triggering a state change. 'Trigger' action can only support to trigger public methods that inherit from MonoBehaviour with no parameters of script file.
Trigger action format:
{{
  "type": "Trigger",
  "source_object_name": "<string>",       // Name of the source object that triggers the event
  "triggerring_time": <float>, 			      // Duration of the trigger
  "source_object_fileID": <long>,         // FileID of the source object in Unity scene file
  "condition": "<string>",                // Trigger condition description (may include script ID, GUID, serialization config, expected behavior calls)
  "triggerring_events": [                 // List of events during the Trigger process, these events will be triggered witin one frame.
    // 0 or more event units
    {{
      "methodCallUnits": [                // An event unit containing 0 or more methodCallUnit
        {{
          "script_fileID": <long>,       // FileID of the target MonoBehaviour Component
          "method_name": "<string>",     // Name of public method with no parameters to call
          "parameter_fileID": []         // No need to fill. Must be empty.
        }}
      ]
    }}
  ],
  "triggerred_events": [                  // List of events after 'triggering_events' have completed, 'triggerred_events' will be executed after waiting for the triggering time. These events will also be triggered within one frame.
    	// 0 or more event units
  ]
}}
- **Transform**: A Transform describes translation, rotation, and scale operations on an object, used to implement incremental adjustments (delta) of object states within an action unit. It can support to execute 'Trigger' action simultaneously.
Transform action format:
{{
  "type": "Transform",
  "source_object_name": "<string>",        // Target object name
  "source_object_fileID": <long>,          // FileID of the object in Unity scene
  "delta_position": {{                     // Position delta (offset)
    "x": <float>,
    "y": <float>,
    "z": <float>
  }},
  "delta_rotation": {{                     // Rotation delta (offset)
    "x": <float>,
    "y": <float>,
    "z": <float>
  }},
  "delta_scale": {{                        // Scale delta (offset)
    "x": <float>,
    "y": <float>,
    "z": <float>
  }},
  "triggerring_events": [                 // List of events during the Trigger process, these events will be triggered witin one frame.
        // 0 or more event units
        {{
          "methodCallUnits": [                // An event unit containing 0 or more methodCallUnit
            {{
              "script_fileID": <long>,     // FileID of the target MonoBehaviour Component
              "method_name": "<string>",     // Name of public method with no parameters to call
              "parameter_fileID": []         // No need to fill. Must be empty.
            }}
          ]
        }}
      ],
  "triggerred_events": [                  // List of events after 'triggering_events' have completed, 'triggerred_events' will be executed after waiting for the triggering time. These events will also be triggered within one frame.
            // 0 or more event units
      ],
  "triggerring_time": <float>                  // Duration of the action
}}
**Redundancy Avoidance Policy:**
- If you choose to add a "Trigger" action, please first check if the event will already be triggered naturally by a previous actions. If so, you don't need to add manual "Trigger" actions.
- Please try to avoid adding manual "Trigger" actions. Please wait until we provide you with all the children information to choose 'Trigger' action.
- For scene meta settings on 'm_Calls', you are encouraged to add 'Trigger' action to trigger the event in case that it cannot be triggered automatically.

The 'm_Children' of Transform indicate series of attached child game objects. We can provide the related information of these objects {children_ids} to help formalize your test plans one by one. You can respond with a test plan and respond with "Need_more_Info" be true.
"""

# Test Plan Generation Prompt Templates
TEST_PLAN_FIRST_REQUEST_SCRIPT_TEMPLATE = """Imagine you are helping software test engineers to create comprehensive test plans without delving into the specifics of the code. Test engineers want to test the {app_name} App. One game object we want to test in the scene of '{scene_name}.unity' is '{gobj_name}'.
Despite the events that can be triggered automatically, please choose the event we want to trigger in some conditions. We will provide the source code of the script attached to this gameobjects below. There may be more than one script attached to one gameobject. And the scene meta setting (MonoBehaviour Component) is shown corresponding to the script file shown.
[Source code of script files attached]
'''
{script_source}
'''
[Extracted JSON format of scene meta file] The scene file of '{scene_name}.unity' can specify the detailed settings of gameobjects and its attached Monobehavior. I'll provide you with the related information of game object '{gobj_name}' and its script. The 'fileID' of gameobject '{gobj_name}' is: {gobj_id}. Please specify that the Monobehaviour component in the scene file I provided is the exact settings of the script file attached to the game objects we want to test. Please notice that the 'm_Calls' in MonoBehaviour component are the Interactable events that also need to be triggered manually or automatically to test the scripts. And the Collider component defines the shape of a GameObject for the purpose of physical collisions. 'Has_Rigidbody' indicates whether the gameobject has Rigidbody component. 'Has_Event_Trigger' indicates the gameobject has EventTrigger MonoBehaviour component. Please read the file below.
'''
{scene_meta}
'''
[Format of Test Plans] The test plan should contain actions chosen from the action list: ['Grab', 'Trigger', 'Transform']. You should choose these actions according to the related information of the target gameobject you want to interact with. Use 'm_PrefabInstance' fileID as the target GameObject's 'source_object_fileID' if it has 'PrefabInstance' component. Please remind that 'Grab' and 'Transform' can only interact with gameobjects that have Rigidbody component. 'Trigger' action can only interact with gameobjects that have Rigidbody or Collider or EventTrigger component, or their attached script has class inherit from UnityEngine.Events. In their attached scripts, there may be interfaces or APIs to indicate that you can only interact with these gameobjects using specific action. Also, if the target GameObject is called "Player" or "player", please do not choose 'Grab' and 'Transform' actions. Also, do not directly perform actions on the controllers that may derive from XR Interaction Toolkit, also do not directly perform actions on our test agent. \n\nPlease structure your response in the following JSON format:
'''
{{
  "taskUnits": [
    {{
      "actionUnits": [
        {{
          "type": "Grab",
          "source_object_name": {{source_object_name}},
          "source_object_fileID": {{source_object_fileID}},
          "target_object_name": {{target_object_name}},
          "target_object_fileID": {{target_object_fileID}}
        }}
      ]
    }},
    {{
      "actionUnits": [
        {{
          "type": "Trigger",
          "source_object_name": {{source_object_name}},
          "triggerring_time": {{triggerring_time}},
          "source_object_fileID": {{source_object_fileID}},
          "condition": "Trigger condition description (may include script ID, GUID, serialization config, expected behavior calls)",
          "triggerring_events": [
            {{
              "methodCallUnits": [
                {{
                  "script_fileID": {{script_fileID}},
                  "method_name": {{method_name}},
                  "parameter_fileID": [{{parameter_fileID}}]
                }}
              ]
            }}
          ]
        }}
      ]
    }},
    {{
      "actionUnits": [
        {{
          "type": "Transform",
          "source_object_name": {{source_object_name}},
          "source_object_fileID": {{source_object_fileID}},
          "delta_position": {{
            "x": {{x}},
            "y": {{y}},
            "z": {{z}}
          }},
          "delta_rotation": {{
            "x": {{x}},
            "y": {{y}},
            "z": {{z}}
          }},
          "delta_scale": {{
            "x": {{x}},
            "y": {{y}},
            "z": {{z}}
          }},
          "triggerring_events": [
            {{
              "methodCallUnits": [
                {{
                  "script_fileID": {{script_fileID}},
                  "method_name": {{method_name}},
                  "parameter_fileID": [{{parameter_fileID}}]
                }}
              ]
            }}
          ],
          "triggerred_events": [
          ],
          "triggerring_time": {{triggerring_time}}
          }}
      ]
    }}
  ],
  "Need_more_Info": true/false
}}
'''
**Action Type Guidelines:**
- **Grab**: Grab or pick up source object and drop it to the target object or position.
Grab action format1:
{{
  "type": "Grab",
  "source_object_name": "<string>",       // Name of the agent or object initiating the grab
  "source_object_fileID": <long>,         // FileID of the source object in the Unity scene file
  "target_object_name": "<string>",       // Name of the target object being grabbed
  "target_object_fileID": <long>          // FileID of the target object in the Unity scene file
}}
Grab action format2:
{{
  "type": "Grab",
  "source_object_name": "<string>",       // Name of the source object
  "source_object_fileID": <long>,         // FileID of the source object in the Unity scene file
  "target_position": {{                    // Target world position to which the object should be moved
    "x": "<float>",
    "y": "<float>",
    "z": "<float>"
  }}
}}
- **Trigger**: Trigger describes the triggering process in interactive actions, mainly used to simulate the player's interaction with objects in VR scenes, such as clicking a button, pulling a lever, or triggering a state change. 'Trigger' action can only support to trigger public methods that inherit from MonoBehaviour with no parameters of script file.
Trigger action format:
{{
  "type": "Trigger",
  "source_object_name": "<string>",       // Name of the source object that triggers the event
  "triggerring_time": <float>, 			      // Duration of the trigger
  "source_object_fileID": <long>,         // FileID of the source object in Unity scene file
  "condition": "<string>",                // Trigger condition description (may include script ID, GUID, serialization config, expected behavior calls)
  "triggerring_events": [                 // List of events during the Trigger process, these events will be triggered witin one frame.
    // 0 or more event units
    {{
      "methodCallUnits": [                // An event unit containing 0 or more methodCallUnit
        {{
          "script_fileID": <long>,       // FileID of the target MonoBehaviour Component
          "method_name": "<string>",     // Name of public method with no parameters to call
          "parameter_fileID": []         // No need to fill. Must be empty.
        }}
      ]
    }}
  ],
  "triggerred_events": [                  // List of events after 'triggering_events' have completed, 'triggerred_events' will be executed after waiting for the triggering time. These events will also be triggered within one frame.
    	// 0 or more event units
  ]
}}
- **Transform**: A Transform describes translation, rotation, and scale operations on an object, used to implement incremental adjustments (delta) of object states within an action unit. It can support to execute 'Trigger' action simultaneously.
Transform action format:
{{
  "type": "Transform",
  "source_object_name": "<string>",        // Target object name
  "source_object_fileID": <long>,          // FileID of the object in Unity scene
  "delta_position": {{                     // Position delta (offset)
    "x": <float>,
    "y": <float>,
    "z": <float>
  }},
  "delta_rotation": {{                     // Rotation delta (offset)
    "x": <float>,
    "y": <float>,
    "z": <float>
  }},
  "delta_scale": {{                        // Scale delta (offset)
    "x": <float>,
    "y": <float>,
    "z": <float>
  }},
  "triggerring_events": [                 // List of events during the Trigger process, these events will be triggered witin one frame.
        // 0 or more event units
        {{
          "methodCallUnits": [                // An event unit containing 0 or more methodCallUnit
            {{
              "script_fileID": <long>,     // FileID of the target MonoBehaviour Component
              "method_name": "<string>",     // Name of public method with no parameters to call
              "parameter_fileID": []         // No need to fill. Must be empty.
            }}
          ]
        }}
      ],
  "triggerred_events": [                  // List of events after 'triggering_events' have completed, 'triggerred_events' will be executed after waiting for the triggering time. These events will also be triggered within one frame.
            // 0 or more event units
      ],
  "triggerring_time": <float>                  // Duration of the action
}}
**Redundancy Avoidance Policy:**
- If you choose to add a "Trigger" action, please first check if the event will already be triggered naturally by a previous actions. If so, you don't need to add manual "Trigger" actions.
- Please try to avoid adding manual "Trigger" actions. Please wait until we provide you with all the children information to choose 'Trigger' action.
- For scene meta settings on 'm_Calls', you are encouraged to add 'Trigger' action to trigger the event in case that it cannot be triggered automatically.

The 'm_Children' of Transform indicate series of attached child game objects. We can provide the related information of these objects {children_ids} to help formalize your test plans one by one."""

# Test Plan Generation Prompt Templates
TEST_PLAN_FIRST_REQUEST_NO_CHILD_TEMPLATE = """Imagine you are helping software test engineers to create comprehensive test plans without delving into the specifics of the code. Test engineers want to test the {app_name} App. One game object we want to test in the scene of '{scene_name}.unity' is '{gobj_name}'.
Despite the events that can be triggered automatically, please choose the event we want to trigger in some conditions. We will provide the source code attached to this gameobjects below.
[Extracted JSON format of scene meta file] The scene file of '{scene_name}.unity' can specify the detailed settings of gameobjects and its attached Monobehavior. I'll provide you with the related information of game object '{gobj_name}' and its script. The 'fileID' of gameobject '{gobj_name}' is: {gobj_id}. Please specify that the Monobehaviour component in the scene file I provided is the exact settings of the script file attached to the game objects we want to test. Please notice that the 'm_Calls' in MonoBehaviour component are the Interactable events that also need to be triggered manually or automatically to test the scripts. And the Collider component defines the shape of a GameObject for the purpose of physical collisions. 'Has_Rigidbody' indicates whether the gameobject has Rigidbody component. 'Has_Event_Trigger' indicates the gameobject has EventTrigger MonoBehaviour component. Please read the file below.
'''
{scene_meta}
'''
[Format of Test Plans] The test plan should contain actions chosen from the action list: ['Grab', 'Trigger', 'Transform']. You should choose these actions according to the related information of the target gameobject you want to interact with. Use 'm_PrefabInstance' fileID as the target GameObject's 'source_object_fileID' if it has 'PrefabInstance' component. Please remind that 'Grab' and 'Transform' can only interact with gameobjects that have Rigidbody component. 'Trigger' action can only interact with gameobjects that have Rigidbody or Collider or EventTrigger component, or their attached script has class inherit from UnityEngine.Events. In their attached scripts, there may be interfaces or APIs to indicate that you can only interact with these gameobjects using specific action. Also, if the target GameObject is called "Player" or "player", please do not choose 'Grab' and 'Transform' actions. Also, do not directly interact with controllers that may derive from XR Interaction Toolkit, also do not directly interact with our test agent. \n\nPlease structure your response in the following JSON format:
'''
{{
  "taskUnits": [
    {{
      "actionUnits": [
        {{
          "type": "Grab",
          "source_object_name": {{source_object_name}},
          "source_object_fileID": {{source_object_fileID}},
          "target_object_name": {{target_object_name}},
          "target_object_fileID": {{target_object_fileID}}
        }}
      ]
    }},
    {{
      "actionUnits": [
        {{
          "type": "Trigger",
          "source_object_name": {{source_object_name}},
          "triggerring_time": {{triggerring_time}},
          "source_object_fileID": {{source_object_fileID}},
          "condition": "Trigger condition description (may include script ID, GUID, serialization config, expected behavior calls)",
          "triggerring_events": [
            {{
              "methodCallUnits": [
                {{
                  "script_fileID": {{script_fileID}},
                  "method_name": {{method_name}},
                  "parameter_fileID": [{{parameter_fileID}}]
                }}
              ]
            }}
          ]
        }}
      ]
    }},
    {{
      "actionUnits": [
        {{
          "type": "Transform",
          "source_object_name": {{source_object_name}},
          "source_object_fileID": {{source_object_fileID}},
          "delta_position": {{
            "x": {{x}},
            "y": {{y}},
            "z": {{z}}
          }},
          "delta_rotation": {{
            "x": {{x}},
            "y": {{y}},
            "z": {{z}}
          }},
          "delta_scale": {{
            "x": {{x}},
            "y": {{y}},
            "z": {{z}}
          }},
          "triggerring_events": [
            {{
              "methodCallUnits": [
                {{
                  "script_fileID": {{script_fileID}},
                  "method_name": {{method_name}},
                  "parameter_fileID": [{{parameter_fileID}}]
                }}
              ]
            }}
          ],
          "triggerred_events": [
          ],
          "triggerring_time": {{triggerring_time}}
          }}
      ]
    }}
  ],
  "Need_more_Info": true/false
}}
'''
**Action Type Guidelines:**
- **Grab**: Grab or pick up source object and drop it to the target object or position.
Grab action format1:
{{
  "type": "Grab",
  "source_object_name": "<string>",       // Name of the agent or object initiating the grab
  "source_object_fileID": <long>,         // FileID of the source object in the Unity scene file
  "target_object_name": "<string>",       // Name of the target object being grabbed
  "target_object_fileID": <long>          // FileID of the target object in the Unity scene file
}}
Grab action format2:
{{
  "type": "Grab",
  "source_object_name": "<string>",       // Name of the source object
  "source_object_fileID": <long>,         // FileID of the source object in the Unity scene file
  "target_position": {{                    // Target world position to which the object should be moved
    "x": "<float>",
    "y": "<float>",
    "z": "<float>"
  }}
}}
- **Trigger**: Trigger describes the triggering process in interactive actions, mainly used to simulate the player's interaction with objects in VR scenes, such as clicking a button, pulling a lever, or triggering a state change. 'Trigger' action can only support to trigger public methods that inherit from MonoBehaviour with no parameters of script file.
Trigger action format:
{{
  "type": "Trigger",
  "source_object_name": "<string>",       // Name of the source object that triggers the event
  "triggerring_time": <float>, 			      // Duration of the trigger
  "source_object_fileID": <long>,         // FileID of the source object in Unity scene file
  "condition": "<string>",                // Trigger condition description (may include script ID, GUID, serialization config, expected behavior calls)
  "triggerring_events": [                 // List of events during the Trigger process, these events will be triggered witin one frame.
    // 0 or more event units
    {{
      "methodCallUnits": [                // An event unit containing 0 or more methodCallUnit
        {{
          "script_fileID": <long>,       // FileID of the target MonoBehaviour Component
          "method_name": "<string>",     // Name of public method with no parameters to call
          "parameter_fileID": []         // No need to fill. Must be empty.
        }}
      ]
    }}
  ],
  "triggerred_events": [                  // List of events after 'triggering_events' have completed, 'triggerred_events' will be executed after waiting for the triggering time. These events will also be triggered within one frame.
    	// 0 or more event units
  ]
}}
- **Transform**: A Transform describes translation, rotation, and scale operations on an object, used to implement incremental adjustments (delta) of object states within an action unit. It can support to execute 'Trigger' action simultaneously.
Transform action format:
{{
  "type": "Transform",
  "source_object_name": "<string>",        // Target object name
  "source_object_fileID": <long>,          // FileID of the object in Unity scene
  "delta_position": {{                     // Position delta (offset)
    "x": <float>,
    "y": <float>,
    "z": <float>
  }},
  "delta_rotation": {{                     // Rotation delta (offset)
    "x": <float>,
    "y": <float>,
    "z": <float>
  }},
  "delta_scale": {{                        // Scale delta (offset)
    "x": <float>,
    "y": <float>,
    "z": <float>
  }},
  "triggerring_events": [                 // List of events during the Trigger process, these events will be triggered witin one frame.
        // 0 or more event units
        {{
          "methodCallUnits": [                // An event unit containing 0 or more methodCallUnit
            {{
              "script_fileID": <long>,     // FileID of the target MonoBehaviour Component
              "method_name": "<string>",     // Name of public method with no parameters to call
              "parameter_fileID": []         // No need to fill. Must be empty.
            }}
          ]
        }}
      ],
  "triggerred_events": [                  // List of events after 'triggering_events' have completed, 'triggerred_events' will be executed after waiting for the triggering time. These events will also be triggered within one frame.
            // 0 or more event units
      ],
  "triggerring_time": <float>                  // Duration of the action
}}
**Redundancy Avoidance Policy:**
- If you choose to add a "Trigger" action, please first check if the event will already be triggered naturally by a previous actions. If so, you don't need to add manual "Trigger" actions.
- Please try to avoid adding manual "Trigger" actions. Please wait until we provide you with all the children information to choose 'Trigger' action.
- For scene meta settings on 'm_Calls', you are encouraged to add 'Trigger' action to trigger the event in case that it cannot be triggered automatically.

Please give me one test plan based on all the information I provided to ensure code coverage. If you need other information to finalize this test plan, Please also respond with a test plan and respond with "Need_more_Info" be true."""

# Test Plan Generation Prompt Templates
TEST_PLAN_FIRST_REQUEST_NO_CHILD_SCRIPT_TEMPLATE = """Imagine you are helping software test engineers to create comprehensive test plans without delving into the specifics of the code. Test engineers want to test the {app_name} App. One game object we want to test in the scene of '{scene_name}.unity' is '{gobj_name}'.
Despite the events that can be triggered automatically, please choose the event we want to trigger in some conditions. We will provide the source code of the script attached to this gameobjects below. There may be more than one script attached to one gameobject. And the scene meta setting (MonoBehaviour Component) is shown corresponding to the script file shown.
[Source code of script files attached]
'''
{script_source}
'''
[Extracted JSON format of scene meta file] The scene file of '{scene_name}.unity' can specify the detailed settings of gameobjects and its attached Monobehavior. I'll provide you with the related information of game object '{gobj_name}' and its script. The 'fileID' of gameobject '{gobj_name}' is: {gobj_id}. Please specify that the Monobehaviour component in the scene file I provided is the exact settings of the script file attached to the game objects we want to test. Please notice that the 'm_Calls' in MonoBehaviour component are the Interactable events that also need to be triggered manually or automatically to test the scripts. And the Collider component defines the shape of a GameObject for the purpose of physical collisions. 'Has_Rigidbody' indicates whether the gameobject has Rigidbody component. 'Has_Event_Trigger' indicates the gameobject has EventTrigger MonoBehaviour component. Please read the file below.
'''
{scene_meta}
'''
[Format of Test Plans] The test plan should contain actions chosen from the action list: ['Grab', 'Trigger', 'Transform']. You should choose these actions according to the related information of the target gameobject you want to interact with. Use 'm_PrefabInstance' fileID as the target GameObject's 'source_object_fileID' if it has 'PrefabInstance' component. Please remind that 'Grab' and 'Transform' can only interact with gameobjects that have Rigidbody component. 'Trigger' action can only interact with gameobjects that have Rigidbody or Collider or EventTrigger component, or their attached script has class inherit from UnityEngine.Events. In their attached scripts, there may be interfaces or APIs to indicate that you can only interact with these gameobjects using specific action. Also, if the target GameObject is called "Player" or "player", please do not choose 'Grab' and 'Transform' actions. Also, do not directly perform actions on the controllers that may derive from XR Interaction Toolkit, also do not directly perform actions on our test agent. \n\nPlease structure your response in the following JSON format:
'''
{{
  "taskUnits": [
    {{
      "actionUnits": [
        {{
          "type": "Grab",
          "source_object_name": {{source_object_name}},
          "source_object_fileID": {{source_object_fileID}},
          "target_object_name": {{target_object_name}},
          "target_object_fileID": {{target_object_fileID}}
        }}
      ]
    }},
    {{
      "actionUnits": [
        {{
          "type": "Trigger",
          "source_object_name": {{source_object_name}},
          "triggerring_time": {{triggerring_time}},
          "source_object_fileID": {{source_object_fileID}},
          "condition": "Trigger condition description (may include script ID, GUID, serialization config, expected behavior calls)",
          "triggerring_events": [
            {{
              "methodCallUnits": [
                {{
                  "script_fileID": {{script_fileID}},
                  "method_name": {{method_name}},
                  "parameter_fileID": [{{parameter_fileID}}]
                }}
              ]
            }}
          ]
        }}
      ]
    }},
    {{
      "actionUnits": [
        {{
          "type": "Transform",
          "source_object_name": {{source_object_name}},
          "source_object_fileID": {{source_object_fileID}},
          "delta_position": {{
            "x": {{x}},
            "y": {{y}},
            "z": {{z}}
          }},
          "delta_rotation": {{
            "x": {{x}},
            "y": {{y}},
            "z": {{z}}
          }},
          "delta_scale": {{
            "x": {{x}},
            "y": {{y}},
            "z": {{z}}
          }},
          "triggerring_events": [
            {{
              "methodCallUnits": [
                {{
                  "script_fileID": {{script_fileID}},
                  "method_name": {{method_name}},
                  "parameter_fileID": [{{parameter_fileID}}]
                }}
              ]
            }}
          ],
          "triggerred_events": [
          ],
          "triggerring_time": {{triggerring_time}}
          }}
      ]
    }}
  ],
  "Need_more_Info": true/false
}}
'''
**Action Type Guidelines:**
- **Grab**: Grab or pick up source object and drop it to the target object or position.
Grab action format1:
{{
  "type": "Grab",
  "source_object_name": "<string>",       // Name of the agent or object initiating the grab
  "source_object_fileID": <long>,         // FileID of the source object in the Unity scene file
  "target_object_name": "<string>",       // Name of the target object being grabbed
  "target_object_fileID": <long>          // FileID of the target object in the Unity scene file
}}
Grab action format2:
{{
  "type": "Grab",
  "source_object_name": "<string>",       // Name of the source object
  "source_object_fileID": <long>,         // FileID of the source object in the Unity scene file
  "target_position": {{                    // Target world position to which the object should be moved
    "x": "<float>",
    "y": "<float>",
    "z": "<float>"
  }}
}}
- **Trigger**: Trigger describes the triggering process in interactive actions, mainly used to simulate the player's interaction with objects in VR scenes, such as clicking a button, pulling a lever, or triggering a state change. 'Trigger' action can only support to trigger public methods that inherit from MonoBehaviour with no parameters of script file.
Trigger action format:
{{
  "type": "Trigger",
  "source_object_name": "<string>",       // Name of the source object that triggers the event
  "triggerring_time": <float>, 			      // Duration of the trigger
  "source_object_fileID": <long>,         // FileID of the source object in Unity scene file
  "condition": "<string>",                // Trigger condition description (may include script ID, GUID, serialization config, expected behavior calls)
  "triggerring_events": [                 // List of events during the Trigger process, these events will be triggered witin one frame.
    // 0 or more event units
    {{
      "methodCallUnits": [                // An event unit containing 0 or more methodCallUnit
        {{
          "script_fileID": <long>,       // FileID of the target MonoBehaviour Component
          "method_name": "<string>",     // Name of public method with no parameters to call
          "parameter_fileID": []         // No need to fill. Must be empty.
        }}
      ]
    }}
  ],
  "triggerred_events": [                  // List of events after 'triggering_events' have completed, 'triggerred_events' will be executed after waiting for the triggering time. These events will also be triggered within one frame.
    	// 0 or more event units
  ]
}}
- **Transform**: A Transform describes translation, rotation, and scale operations on an object, used to implement incremental adjustments (delta) of object states within an action unit. It can support to execute 'Trigger' action simultaneously.
Transform action format:
{{
  "type": "Transform",
  "source_object_name": "<string>",        // Target object name
  "source_object_fileID": <long>,          // FileID of the object in Unity scene
  "delta_position": {{                     // Position delta (offset)
    "x": <float>,
    "y": <float>,
    "z": <float>
  }},
  "delta_rotation": {{                     // Rotation delta (offset)
    "x": <float>,
    "y": <float>,
    "z": <float>
  }},
  "delta_scale": {{                        // Scale delta (offset)
    "x": <float>,
    "y": <float>,
    "z": <float>
  }},
  "triggerring_events": [                 // List of events during the Trigger process, these events will be triggered witin one frame.
        // 0 or more event units
        {{
          "methodCallUnits": [                // An event unit containing 0 or more methodCallUnit
            {{
              "script_fileID": <long>,     // FileID of the target MonoBehaviour Component
              "method_name": "<string>",     // Name of public method with no parameters to call
              "parameter_fileID": []         // No need to fill. Must be empty.
            }}
          ]
        }}
      ],
  "triggerred_events": [                  // List of events after 'triggering_events' have completed, 'triggerred_events' will be executed after waiting for the triggering time. These events will also be triggered within one frame.
            // 0 or more event units
      ],
  "triggerring_time": <float>                  // Duration of the action
}}
**Redundancy Avoidance Policy:**
- If you choose to add a "Trigger" action, please first check if the event will already be triggered naturally by a previous actions. If so, you don't need to add manual "Trigger" actions.
- Please try to avoid adding manual "Trigger" actions. Please wait until we provide you with all the children information to choose 'Trigger' action.
- For scene meta settings on 'm_Calls', you are encouraged to add 'Trigger' action to trigger the event in case that it cannot be triggered automatically.

Please give me one test plan based on the information I provided to trigger all the events to ensure code coverage. If you need other information to finalize this test plan, Please also respond with a test plan and respond with "Need_more_Info" be true.
"""


TEST_PLAN_CHILD_REQUEST_TEMPLATE = """The children is "{child_name}": {{fileID: {child_id}}}. The direct parent of this gameobject is "{parent_name}". We only present the child with attached script. And the {child_name} gameobject which has attached script's information is below. There may be more than one script attached to one gameobject. Please specify that the Monobehaviour component in the scene file I provided is the settings of the script file attached to the game objects. And the scene meta setting (MonoBehaviour Component) is shown corresponding to the script file shown.
[Source code of 1st script files attached]
'''
{script_source}
'''
[Extracted JSON format of scene meta file]
'''
{child_scene_meta}
'''

Please give me one test plan to trigger all the events to ensure code coverage. Do not include former test plans if they are already perfect. Please respond with the Test Plans format and you must conform the redundancy avoidance policy I gave you. If you need other information, Please also respond with a test plan and respond with "Need_more_Info" be true."""

# Tag Logic Test Request Template
TAG_TEST_REQUEST_TEMPLATE = """Based on the tag logic information, the following gameobjects {needed_gameobject_ids} have corresponding tags with script of gameobject "{child_id}". The information of these gameobjects is below.

{script_sources_and_meta}

Please finalize the test plan based on previous test plans to ensure code coverage. Do not include former test plans if they are already perfect. Please respond with the Test Plans format and you must conform the redundancy avoidance policy I gave you. If you need another information, Please also respond with a draft test plan and respond with "Need_more_Info" be true."""

TAG_LOGIC_REQUEST_TEMPLATE = """Imagine you are helping match corresponding tags between GameObjects to test the scripts. 
 The GameObject is "{gobj_name}": {{fileID: {gobj_id}}}. And the {gobj_name} gameobject which has attached script's information is below. There may be more than one script attached to one gameobject. Please specify that the Monobehaviour component in the scene file I provided is the settings of the script file attached to the game objects. And the scene meta setting (MonoBehaviour Component) is shown corresponding to the script file shown.
[Source code of script files attached]
'''
{combined_script_source}
'''
[Extracted JSON format of scene meta file]
'''
{gobj_scene_meta}
'''
{tag_logic_prompt}
"""

TAG_LOGIC_CHILD_REQUEST_TEMPLATE = """Imagine you are helping match corresponding tags between GameObjects to test the scripts. 
 The children is "{child_name}": {{fileID: {child_id}}}. The direct parent of this gameobject is "{parent_name}". And the {child_name} gameobject which has attached script's information is below. There may be more than one script attached to one gameobject. Please specify that the Monobehaviour component in the scene file I provided is the settings of the script file attached to the game objects. And the scene meta setting (MonoBehaviour Component) is shown corresponding to the script file shown.
[Source code of script files attached]
'''
{combined_script_source}
'''
[Extracted JSON format of scene meta file]
'''
{child_scene_meta}
'''
{tag_logic_prompt}
"""

LAYER_LOGIC_REQUEST_TEMPLATE = """Imagine you are helping match corresponding layers between GameObjects to test the scripts. 
 The GameObject is "{gobj_name}": {{fileID: {gobj_id}}}. And the {gobj_name} gameobject which has attached script's information is below. There may be more than one script attached to one gameobject. Please specify that the Monobehaviour component in the scene file I provided is the settings of the script file attached to the game objects. And the scene meta setting (MonoBehaviour Component) is shown corresponding to the script file shown.
[Source code of script files attached]
'''
{combined_script_source}
'''
[Extracted JSON format of scene meta file]
'''
{gobj_scene_meta}
'''
{tag_logic_prompt}
"""

LAYER_LOGIC_CHILD_REQUEST_MATCHING_TEMPLATE= """Imagine you are helping match corresponding layers between GameObjects to test the scripts. 
 The children is "{child_name}": {{fileID: {child_id}}}. The direct parent of this gameobject is "{parent_name}". And the {child_name} gameobject which has attached script's information is below. There may be more than one script attached to one gameobject. Please specify that the Monobehaviour component in the scene file I provided is the settings of the script file attached to the game objects. And the scene meta setting (MonoBehaviour Component) is shown corresponding to the script file shown.
[Source code of script files attached]
'''
{combined_script_source}
'''
[Extracted JSON format of scene meta file]
'''
{child_scene_meta}
'''
{tag_logic_prompt}
"""

# Tag Logic Child Request Template (for children with tag_logic_info)
TAG_LOGIC_CHILD_REQUEST_TEMPLATE_NEW = """The children is "{child_name}": {{fileID: {child_id}}}. The direct parent of this gameobject is "{parent_name}". We only present the child with attached script. And the {child_name} gameobject which has attached script's information is below. There may be more than one script attached to one gameobject. Please specify that the Monobehaviour component in the scene file I provided is the settings of the script file attached to the game objects. And the scene meta setting (MonoBehaviour Component) is shown corresponding to the script file shown.
[Source code of 1st script files attached]
'''
{combined_script_source}
'''
[Extracted JSON format of scene meta file]
'''
{child_scene_meta}
'''

The following gameobjects {needed_gameobject_ids} have matching tags with .CompareTag() logic detected in the source script of gameobject "{child_id}". So, you need to add actionUnits to interact with these gameobjects in order to invocate the methods of gameobject "{child_id}" consequently. The information of these gameobjects are belows:
{script_sources_and_meta}

Please finalize the test plan based on previous test plans to ensure code coverage. Do not include former test plans if they are already perfect. Please respond with the Test Plans format and you must conform the redundancy avoidance policy I gave you. If you need another information, Please also respond with a draft test plan and respond with "Need_more_Info" be true.
"""

LAYER_LOGIC_CHILD_REQUEST_TEMPLATE = """The children is "{child_name}": {{fileID: {child_id}}}. The direct parent of this gameobject is "{parent_name}". We only present the child with attached script. And the {child_name} gameobject which has attached script's information is below. There may be more than one script attached to one gameobject. Please specify that the Monobehaviour component in the scene file I provided is the settings of the script file attached to the game objects. And the scene meta setting (MonoBehaviour Component) is shown corresponding to the script file shown.
[Source code of 1st script files attached]
'''
{combined_script_source}
'''
[Extracted JSON format of scene meta file]
'''
{child_scene_meta}
'''

The following gameobjects {needed_gameobject_ids} have matching layers with .NameToLayer() logic detected in the source script of gameobject "{child_id}". So, you need to add actionUnits to interact with these gameobjects in order to invocate the methods of gameobject "{child_id}" consequently. The information of these gameobjects are belows:
{script_sources_and_meta}

Please finalize the test plan based on previous test plans to ensure code coverage. Do not include former test plans if they are already perfect. Please respond with the Test Plans format and you must conform the redundancy avoidance policy I gave you. If you need another information, Please also respond with a draft test plan and respond with "Need_more_Info" be true.
"""

# GameObject Find Logic Child Request Template (for children with gameobject_find_info)
GAMEOBJECT_FIND_LOGIC_CHILD_REQUEST_TEMPLATE = """The children is "{child_name}": {{fileID: {child_id}}}. The direct parent of this gameobject is "{parent_name}". We only present the child with attached script. And the {child_name} gameobject which has attached script's information is below. There may be more than one script attached to one gameobject. Please specify that the Monobehaviour component in the scene file I provided is the settings of the script file attached to the game objects. And the scene meta setting (MonoBehaviour Component) is shown corresponding to the script file shown.
[Source code of 1st script files attached]
'''
{combined_script_source}
'''
[Extracted JSON format of scene meta file]
'''
{child_scene_meta}
'''

The following gameobjects {needed_gameobject_ids} have GameObject.Find() logic detected in the source script of gameobject "{child_id}". So, you need to add actionUnits to interact with these gameobjects in order to invocate the methods of gameobject "{child_id}" consequently. The information of these gameobjects are belows:
{script_sources_and_meta}

Please finalize the test plan based on previous test plans to ensure code coverage. Do not include former test plans if they are already perfect. Please respond with the Test Plans format and you must conform the redundancy avoidance policy I gave you. If you need another information, Please also respond with a draft test plan and respond with "Need_more_Info" be true.
"""

# GameObject Find Logic Child Request Template (for children with gameobject_find_info)
GAMEOBJECT_INSTANTIATE_LOGIC_CHILD_REQUEST_TEMPLATE = """The children is "{child_name}": {{fileID: {child_id}}}. The direct parent of this gameobject is "{parent_name}". We only present the child with attached script. And the {child_name} gameobject which has attached script's information is below. There may be more than one script attached to one gameobject. Please specify that the Monobehaviour component in the scene file I provided is the settings of the script file attached to the game objects. And the scene meta setting (MonoBehaviour Component) is shown corresponding to the script file shown.
[Source code of 1st script files attached]
'''
{combined_script_source}
'''
[Extracted JSON format of scene meta file]
'''
{child_scene_meta}
'''

The following gameobjects {needed_gameobject_ids} have Instantiate() logic detected in the source script of gameobject "{child_id}". So, you need to add actionUnits to interact with these gameobjects in order to invocate the methods of gameobject "{child_id}" consequently. The information of these gameobjects are belows:
{script_sources_and_meta}

Please finalize the test plan based on previous test plans to ensure code coverage. Do not include former test plans if they are already perfect. Please respond with the Test Plans format and you must conform the redundancy avoidance policy I gave you. If you need another information, Please also respond with a draft test plan and respond with "Need_more_Info" be true.
"""

# Tag Logic Main GameObject Request Template (for main gameobjects with tag_logic_info)
TAG_LOGIC_MAIN_REQUEST_TEMPLATE = """The gameobject is "{gobj_name}": {{fileID: {gobj_id}}}. Please use the source code of the scripts attached to the gameobject and the extracted JSON format of scene meta file we provided in the last conversation to finalize the test plan.

The following gameobjects {needed_gameobject_ids} have matching tags with .CompareTag() logic detected in the source script of gameobject "{gobj_id}". So, you need to add actionUnits to interact with these gameobjects in order to invocate the methods of gameobject "{gobj_id}" consequently. The information of these gameobjects are belows:
{script_sources_and_meta}

Please finalize the test plan based on previous test plans to ensure code coverage. Do not include former test plans if they are already perfect. Please respond with the Test Plans format and you must conform the redundancy avoidance policy I gave you. If you need another information, Please also respond with a draft test plan and respond with "Need_more_Info" be true.
"""

# Layer Logic Main GameObject Request Template (for main gameobjects with layer_logic_info)
LAYER_LOGIC_MAIN_REQUEST_TEMPLATE = """The gameobject is "{gobj_name}": {{fileID: {gobj_id}}}. Please use the source code of the scripts attached to the gameobject and the extracted JSON format of scene meta file we provided in the last conversation to finalize the test plan.

The following gameobjects {needed_gameobject_ids} have matching layers with .NameToLayer() logic detected in the source script of gameobject "{gobj_id}". So, you need to add actionUnits to interact with these gameobjects in order to invocate the methods of gameobject "{gobj_id}" consequently. The information of these gameobjects are belows:
{script_sources_and_meta}

Please finalize the test plan based on previous test plans to ensure code coverage. Do not include former test plans if they are already perfect. Please respond with the Test Plans format and you must conform the redundancy avoidance policy I gave you. If you need another information, Please also respond with a draft test plan and respond with "Need_more_Info" be true.
"""

# GameObject Find Logic Main Request Template (for main gameobjects with gameobject_find_info)
GAMEOBJECT_FIND_LOGIC_MAIN_REQUEST_TEMPLATE = """The gameobject is "{gobj_name}": {{fileID: {gobj_id}}}. Please use the source code of the scripts attached to the gameobject and the extracted JSON format of scene meta file we provided in the last conversation to finalize the test plan.

The following gameobjects {needed_gameobject_ids} have GameObject.Find() logic detected in the source script of gameobject "{gobj_id}". So, you need to add actionUnits to interact with these gameobjects in order to invocate the methods of gameobject "{gobj_id}" consequently. The information of these gameobjects are belows:
{script_sources_and_meta}

Please finalize the test plan based on previous test plans to ensure code coverage. Do not include former test plans if they are already perfect. Please respond with the Test Plans format and you must conform the redundancy avoidance policy I gave you. If you need another information, Please also respond with a draft test plan and respond with "Need_more_Info" be true.
"""

# GameObject Instantiate Logic Main Request Template (for main gameobjects with gameobject_instantiate_info)
GAMEOBJECT_INSTANTIATE_LOGIC_MAIN_REQUEST_TEMPLATE = """The gameobject is "{gobj_name}": {{fileID: {gobj_id}}}. Please use the source code of the scripts attached to the gameobject and the extracted JSON format of scene meta file we provided in the last conversation to finalize the test plan.

The following gameobjects {needed_gameobject_ids} have Instantiate() logic detected in the source script of gameobject "{gobj_id}". So, you need to add actionUnits to interact with these gameobjects in order to invocate the methods of gameobject "{gobj_id}" consequently. The information of these gameobjects are belows:
{script_sources_and_meta}

Please finalize the test plan based on previous test plans to ensure code coverage. Do not include former test plans if they are already perfect. Please respond with the Test Plans format and you must conform the redundancy avoidance policy I gave you. If you need another information, Please also respond with a draft test plan and respond with "Need_more_Info" be true.
"""
# Default values for test plan generation
DEFAULT_APP_NAME = "escapeVr"

# Path configurations for analysis tools
import os
_script_dir = os.path.dirname(os.path.abspath(__file__))
unity_analyzer_path = os.path.join(_script_dir, "UnityDataAnalyzer", "UnityDataAnalyzer.exe")
csharp_analyzer_path = os.path.join(_script_dir, "CSharpScriptAnalyzer", "CSharpAnalyzer.exe")
structure_analyzer_path = os.path.join(_script_dir, "CodeStructureAnalyzer", "CodeStructureAnalyzer.exe")




# OpenAI API Configuration
OPENAI_API_KEY = "sk-..."  # 替换为你从 https://platform.openai.com/api-keys 获得的 API Key
basicUrl_gpt35 = "https://api.openai.com/v1"