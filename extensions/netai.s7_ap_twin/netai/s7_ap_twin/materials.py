from pxr import Gf, Sdf, UsdShade


def make_coverage_material(
    stage, mat_path: str, color: Gf.Vec3f, opacity: float
) -> UsdShade.Material:
    if stage.GetPrimAtPath(mat_path).IsValid():
        stage.RemovePrim(Sdf.Path(mat_path))

    mat    = UsdShade.Material.Define(stage, mat_path)
    shader = UsdShade.Shader.Define(stage, f"{mat_path}/Shader")
    shader.SetSourceAsset("OmniPBR.mdl", "mdl")
    shader.SetSourceAssetSubIdentifier("OmniPBR", "mdl")

    shader.CreateInput("diffuse_color_constant", Sdf.ValueTypeNames.Color3f).Set(color)
    shader.CreateInput("enable_opacity",         Sdf.ValueTypeNames.Bool).Set(True)
    shader.CreateInput("opacity_constant",       Sdf.ValueTypeNames.Float).Set(opacity)

    mat.CreateSurfaceOutput("mdl").ConnectToSource(shader.ConnectableAPI(), "out")
    mat.CreateDisplacementOutput("mdl").ConnectToSource(shader.ConnectableAPI(), "out")
    mat.CreateVolumeOutput("mdl").ConnectToSource(shader.ConnectableAPI(), "out")
    return mat


def bind_material(prim, mat: UsdShade.Material) -> None:
    UsdShade.MaterialBindingAPI(prim).Bind(mat)


def get_shader(stage, mat_path: str) -> UsdShade.Shader | None:
    shader_prim = stage.GetPrimAtPath(f"{mat_path}/Shader")
    if not shader_prim.IsValid():
        return None
    return UsdShade.Shader(shader_prim)
