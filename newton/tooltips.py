"""Hover texts of the sidebar rows; each one sits on the row's label and on its input."""
from .i18n import tr
from . import help_texts as help


def tip(text,*widgets):
    for widget in widgets:
        if widget is not None:widget.setToolTip(tr(text))


def row(form,field,text,*inputs):
    """Label (found through the form) and inputs of one form row."""
    tip(text,form.labelForField(field),field,*inputs)


def apply(panel):
    joint = panel.joint_form
    row(panel.model_form,panel.model_solver,help.TIP_CONTACT_SOLVER)
    tip(help.TIP_PROFILE_APPLY,panel.profile_combo)
    tip(help.TIP_PROFILE_STATUS,panel.profile_status)
    tip(help.TIP_PROFILE_UNLINK,panel.profile_unlink)
    generic = panel.editor.body.layout()
    row(generic,panel.mode,help.TIP_BEHAVIOUR)
    tip(help.TIP_REFERENCE,generic.labelForField(panel.reference_buttons[0]),panel.reference_buttons[0])
    row(joint,panel.name_edit,help.TIP_CONTROL_NAME)
    row(joint,panel.drive,help.TIP_ACTUATOR)
    tip(help.TIP_LIMITS,panel.limited)
    for key,field in (("lower",panel.lower),("upper",panel.upper)):
        row(joint,panel.ranges[key],help.TIP_LIMITS,field)
    row(joint,panel.ranges["target"],help.TIP_TARGET,panel.target)
    row(joint,panel.max_speed,help.TIP_SPEED)
    row(joint,panel.acceleration,help.TIP_ACCELERATION)
    row(joint,panel.deceleration_row,help.TIP_DECELERATION,panel.deceleration)
    row(joint,panel.force,help.TIP_FORCE)

    coupling = panel.coupling_editor
    row(coupling.form,coupling.master,help.TIP_COUPLING_AXIS)
    row(coupling.form,coupling.direction,help.TIP_COUPLING_DIRECTION)
    row(coupling.form,coupling.ratio,help.TIP_COUPLING_RATIO)

    connection = panel.connection_editor
    row(connection.layout(),connection.kind,help.TIP_CONNECTION_TYPE)
    for field in connection.point:row(connection.detail,field,help.TIP_CONNECTION_POINT)
    row(connection.detail,connection.axis_fields,help.TIP_CONNECTION_AXIS,*connection.axis)

    flexible = panel.flexible_editor
    detail = flexible.fields.layout()
    row(flexible.layout(),flexible.kind,help.TIP_FLEX_MATERIAL)
    for field,text in ((flexible.radius,help.TIP_FLEX_RADIUS),(flexible.bend,help.TIP_FLEX_BEND),
                       (flexible.twist,help.TIP_FLEX_TWIST),(flexible.damping,help.TIP_FLEX_DAMPING),
                       (flexible.start,help.TIP_FLEX_START),(flexible.end,help.TIP_FLEX_END)):
        row(detail,field,text)

    row(panel.collision_form,panel.shape,help.TIP_SHAPE)
    body = panel.body_form
    row(body,panel.mass,help.TIP_MASS)
    for key,field,text in (("friction",panel.friction,help.TIP_FRICTION),("bounce",panel.bounce,help.TIP_BOUNCE)):
        row(body,panel.ranges[key],text,field)

    environment = panel.environment
    forms = [item.layout() for item in map(environment.layout().itemAt,range(environment.layout().count())) if item.layout()]
    texts = {"gravity":help.TIP_GRAVITY,"linear_damping":help.TIP_LINEAR_DAMPING,"angular_damping":help.TIP_ANGULAR_DAMPING,
             "floor":help.TIP_GROUND,"attraction":help.TIP_ATTRACTION,"softening":help.TIP_SOFTENING,"initial_velocity":help.TIP_VELOCITY}
    for key,_,widget,button,_ in environment.rows:
        field = button.parentWidget()
        labels = [form.labelForField(field) for form in forms]
        tip(texts[key],widget,field,*labels)
