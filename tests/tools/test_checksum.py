from ptasc.tools.checksum import file_sha256


def test_file_sha256_is_stable(tmp_path):
    path = tmp_path / "sample.bin"
    path.write_bytes(b"ptasc")

    assert file_sha256(path) == file_sha256(path)
    assert len(file_sha256(path)) == 64
