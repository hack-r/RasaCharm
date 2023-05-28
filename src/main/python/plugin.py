import os
import yaml
from rasa.engine.validation import validate
from rasa.engine.training.graph_trainer import load_model
from rasa.engine.graph import ExecutionContext
from rasa.shared.core.domain import Domain
from rasa.shared.importers.autoconfig import TrainingType

from com.intellij.openapi.components import ServiceManager
from com.intellij.openapi.fileEditor import FileEditorManagerListener
from com.intellij.openapi.project import Project
from com.intellij.openapi.vfs import VirtualFileListener, VirtualFileManager
from com.intellij.codeInspection import LocalInspectionTool, ProblemHighlightType, ProblemsHolder

class RasaProjectService:
    def __init__(self, project):
        self.project = project
        self.parse_project()

    def parse_project(self):
        base_path = self.project.getBasePath()
        self.domain_data = self.load_yaml(os.path.join(base_path, 'domain.yml'))
        self.credentials_data = self.load_yaml(os.path.join(base_path, 'credentials.yml'))
        self.endpoints_data = self.load_yaml(os.path.join(base_path, 'endpoints.yml'))
        self.nlu_data = self.load_yaml(os.path.join(base_path, 'data', 'nlu.yml'))
        self.stories_data = self.load_yaml(os.path.join(base_path, 'data', 'stories.yml'))

    @staticmethod
    def load_yaml(path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def check_consistency(self, file):
        try:
            # Create an execution context
            context = ExecutionContext(graph_schema=None, model_id="1")
            # Load the model configuration from the Rasa project files
            model_config = self.load_model_config()
            # Validate the model configuration
            validate(model_config)
        except Exception as e:
            return [str(e)]
        return []

    def load_model_config(self):
        # Specify the paths to the Rasa project files
        domain_path = os.path.join(self.project.getBasePath(), 'domain.yml')
        config_path = os.path.join(self.project.getBasePath(), 'config.yml')
        training_files = [os.path.join(self.project.getBasePath(), 'data')]

        # Load the domain and config data
        domain = Domain.from_path(domain_path)
        config = self.load_yaml(config_path)

        # Return the loaded model configuration
        return load_model(
            domain=domain,
            config=config,
            training_type=TrainingType.BOTH,
            training_data_paths=training_files,
            model_id="1",
        )

class MyFileListener(VirtualFileListener):
    def __init__(self, project):
        self.rasa_service = ServiceManager.getService(project, RasaProjectService)

    def contentsChanged(self, event):
        self.rasa_service.parse_project()


class RasaConsistencyInspection(LocalInspectionTool):
    def checkFile(self, file, manager, isOnTheFly):
        rasa_service = ServiceManager.getService(file.getProject(), RasaProjectService)
        problems = rasa_service.check_consistency(file)

        problems_holder = ProblemsHolder(manager, file, isOnTheFly)
        for problem in problems:
            problems_holder.registerProblem(
                problem,
                ProblemHighlightType.GENERIC_ERROR_OR_WARNING,
            )
        return problems_holder.getResultsArray()


class RasaPluginInitializer:
    @staticmethod
    def init(project):
        rasa_service = RasaProjectService(project)
        ServiceManager.getService(project, RasaProjectService)
        file_listener = MyFileListener(project)
        VirtualFileManager.getInstance().addVirtualFileListener(file_listener)
