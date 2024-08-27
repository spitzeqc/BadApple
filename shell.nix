{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  nativeBuildInputs = with pkgs.buildPackages; [
    python311Packages.pillow
    python311Packages.pygame
  ];
}
