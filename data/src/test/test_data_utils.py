import unittest
import zipfile
from io import BytesIO
from unittest.mock import MagicMock, patch, Mock

import pytest

import geopandas as gpd
from config.config import USE_CRS
from data_utils.park_priority import get_latest_shapefile_url, park_priority
from data_utils.ppr_properties import ppr_properties
from data_utils.vacant_properties import vacant_properties
from shapely.geometry import Point

from google.cloud.storage import Bucket

from data_utils.vacant_properties import google_cloud_bucket

@pytest.fixture(autouse=True)
def mock_gcp_bucket(monkeypatch):
    mock_bucket = MagicMock(spec=Bucket)

    monkeypatch.setattr('classes.featurelayer.google_cloud_bucket', lambda: mock_bucket)

    return mock_bucket


class TestDataUtils(unittest.TestCase):
    """
    Test methods for data utils feature layer classes
    """

    def test_get_latest_shapefile_url(self):
        """
        Test the get_latest_shapefile_url function.
        """
        url = get_latest_shapefile_url()
        self.assertTrue(url.startswith("https://"))
        self.assertTrue(url.endswith(".zip"))

    @patch("data_utils.park_priority.requests.get")
    def test_get_latest_shapefile_url_mock(self, mock_get):
        """
        Test the get_latest_shapefile_url function.
        """
        mock_response = MagicMock()
        mock_response.content = (
            b'<html><a href="https://example.com/shapefile.zip">Shapefile</a></html>'
        )
        mock_get.return_value = mock_response

        url = get_latest_shapefile_url()
        self.assertEqual(url, "https://example.com/shapefile.zip")

    @patch(
        "data_utils.park_priority.requests.get"
    )  # Mock requests.get globally in park_priority
    @patch("geopandas.read_file")
    @patch("geopandas.GeoDataFrame.to_file")  # Mock to_file to prevent actual writing
    @patch("os.path.exists")
    @patch("os.makedirs")
    @patch("zipfile.ZipFile.extract")
    def test_park_priority(
        self,
        mock_extract,
        mock_makedirs,
        mock_exists,
        mock_to_file,
        mock_read_file,
        mock_get,
    ):
        """
        Test the park_priority function with mocking.
        """

        # Simulate that the GeoJSON file does not exist
        mock_exists.return_value = False

        # First call to requests.get (HTML page to get the shapefile URL)
        mock_html_response = MagicMock()
        mock_html_response.content = (
            b'<html><a href="https://example.com/shapefile.zip">Shapefile</a></html>'
        )

        # test comment to see how vulture config works in precommit hook

        # Second call to requests.get (actual shapefile download)
        mock_zip_content = BytesIO()
        with zipfile.ZipFile(mock_zip_content, "w") as zf:
            zf.writestr("Parkserve_ParkPriorityAreas.shp", b"mock shapefile content")

        mock_response = MagicMock()
        mock_response.headers.get.return_value = "1000"  # Mock content-length
        mock_response.iter_content.return_value = [mock_zip_content.getvalue()]

        # Set the side effect for requests.get to return the two different responses
        mock_get.side_effect = [mock_html_response, mock_response]

        # Create a real mock GeoDataFrame with geometries and a CRS
        mock_gdf = gpd.GeoDataFrame(
            {
                "ID": ["42101ABC", "42101DEF", "12345XYZ"],
                "ParkNeed": [5, 3, 1],
                "geometry": [
                    Point(0, 0),
                    Point(1, 1),
                    Point(2, 2),
                ],  # Use actual Point geometries
            },
            crs=USE_CRS,  # Assign the expected CRS
        )

        mock_read_file.return_value = mock_gdf  # Return the mock GeoDataFrame

        # Create a mock primary feature layer
        mock_primary_layer = MagicMock()

        # Run the function
        result = park_priority(mock_primary_layer)

        # Assert that requests.get was called twice (once for HTML, once for shapefile)
        self.assertEqual(mock_get.call_count, 2)

        # Assert that to_file was called once (simulating the write operation)
        mock_to_file.assert_called_once_with("tmp/phl_parks.geojson", driver="GeoJSON")

        # Assert other function calls were made correctly
        mock_read_file.assert_called_once()
        mock_primary_layer.spatial_join.assert_called_once()
        mock_extract.assert_called()

        self.assertEqual(result, mock_primary_layer)

    @patch('data_utils.vacant_properties.google_cloud_bucket')
    @patch('geopandas.read_file')
    def test_ppr_properties(self, mock_gpd, mock_gcs):
        """
        Test the ppr properties layer. Simply construct the class for now to see if it works.
        """
        mock_gdf = gpd.GeoDataFrame({
            'ADDRESS': ['123 Main St'],
            'OWNER1': ['John Doe'],
            'OWNER2': ['Jane Doe'],
            'BLDG_DESC': ['House'],
            'CouncilDistrict': [1],
            'ZoningBaseDistrict': ['R1'],
            'ZipCode': ['19107'],
            'OPA_ID': ['12345'],
            'geometry': [Point(-75.1652, 39.9526)]
        },  crs='EPSG:4326')

        # Set up the mock chain
        mock_blob = Mock()
        mock_blob.exists.return_value = True
        mock_blob.download_as_bytes.return_value = b'dummy bytes'  # The actual bytes don't matter now

        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob

        mock_gcs.return_value = mock_bucket

        # Make read_file return our mock GeoDataFrame
        mock_gpd.return_value = mock_gdf

        ppr_properties(vacant_properties())

    @patch('data_utils.vacant_properties.google_cloud_bucket')
    @patch('geopandas.read_file')
    def test_vacant_properties(self, mock_gpd, mock_gcs):
        """
        Test the vacant properties layer. Simply construct the class to see if it works.
        """
        mock_gdf = gpd.GeoDataFrame({
            'ADDRESS': ['123 Main St'],
            'OWNER1': ['John Doe'],
            'OWNER2': ['Jane Doe'],
            'BLDG_DESC': ['House'],
            'CouncilDistrict': [1],
            'ZoningBaseDistrict': ['R1'],
            'ZipCode': ['19107'],
            'OPA_ID': ['12345'],
            'geometry': [Point(-75.1652, 39.9526)]
        },  crs='EPSG:4326')

        # Set up the mock chain
        mock_blob = Mock()
        mock_blob.exists.return_value = True
        mock_blob.download_as_bytes.return_value = b'dummy bytes'  # The actual bytes don't matter now

        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob

        mock_gcs.return_value = mock_bucket

        # Make read_file return our mock GeoDataFrame
        mock_gpd.return_value = mock_gdf
        vacant_properties()


if __name__ == "__main__":
    unittest.main()
