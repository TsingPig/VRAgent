# VRAgent

VRAgent is a fully automated testing tool for VR scene exploration and action execution. It integrates an LLM-driven approach for test plan generation with HenryLabXR’s open-source EAT framework and VRExplorer. Test engineers can leverage LLMs and our analysis tools to create customized test plans, which can then be imported into VRAgent for automated execution.

## Configuration

- 1). Same as **VRExplorer Configuration**
- 2). **Test Plan Generation:** LLM + RAG / Manual Setting
- 3). **Test Plan Import:** Tools → VRExplorer → Import Test Plan → Browse → Import Test Plan
- 4). **Test Plan Checking:** Verify that a **FileIdManager** is generated in the testing scene and that the ID configuration is correct and complete. Also check whether the target objects to be tested have changed (e.g., whether the testing scripts have been attached).