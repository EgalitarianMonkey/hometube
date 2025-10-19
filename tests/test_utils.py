"""
Essential utility tests.
"""


class TestProjectStructure:
    """Project structure tests."""

    def test_project_directories_exist(self, project_root):
        """Test that main directories exist."""
        required_dirs = ["app", "tests"]  # Removed downloads - it's created at runtime
        for dir_name in required_dirs:
            assert (project_root / dir_name).exists(), f"Directory {dir_name} missing"

    def test_main_files_exist(self, project_root):
        """Test that main files exist."""
        required_files = [
            "app/main.py",
            # app/utils.py removed - migrated to dedicated *_utils modules
            "tests/conftest.py",
            "pyproject.toml",
            "Makefile",
            "requirements/requirements.txt",
        ]
        for file_path in required_files:
            assert (project_root / file_path).exists(), f"File {file_path} missing"


class TestConfiguration:
    """Configuration tests."""

    def test_pyproject_exists(self, project_root):
        """Test that pyproject.toml exists."""
        assert (project_root / "pyproject.toml").exists()

    def test_makefile_exists(self, project_root):
        """Test that Makefile exists."""
        assert (project_root / "Makefile").exists()


class TestBasicFixtures:
    """Basic fixture tests."""

    def test_temp_dir_fixture(self, temp_dir):
        """Test temp_dir fixture."""
        assert temp_dir.exists()
        assert temp_dir.is_dir()

    def test_project_root_fixture(self, project_root):
        """Test project_root fixture."""
        assert project_root.exists()
        assert project_root.is_dir()
        assert (project_root / "app").exists()
