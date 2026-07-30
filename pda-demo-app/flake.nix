{
  description = "For development using uv for easier development without PostmarketOS";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
  };

  outputs =
    { nixpkgs, ... }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems =
        function: nixpkgs.lib.genAttrs systems (system: function nixpkgs.legacyPackages.${system});
    in
    {
      formatter = forAllSystems (pkgs: pkgs.nixfmt);
      devShells = forAllSystems (pkgs: {
        default = pkgs.mkShell {
          packages = [
            pkgs.python3
            pkgs.uv
            pkgs.gtk4
            pkgs.python314Packages.pygobject3
            pkgs.python314Packages.pycairo
          ];
          shellHook = ''
            echo "In dev shell!"
          '';
        };
      });
    };
}
