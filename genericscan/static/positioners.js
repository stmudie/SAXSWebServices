var positionerStruct = {
    SampleTableX: 'SR13ID01HU02IOC01:SMPL_TBL_X_MTR',
    SampleTableY: 'SR13ID01HU02IOC02:SMPL_TBL_Y_MTR',
    GSAXS_X: 'SR13ID01HU02IOC01:GSAX_X_MTR',
    GSAXS_Y: 'SR13ID01HU02IOC01:GSAX_Y_MTR',
    Omega: 'SR13ID01HU02IOC01:GSAX_OMG_MTR',
    Phi: 'SR13ID01HU02IOC01:SMPL_PHI_MTR',
    Energy: 'SR13ID01HU01:ENERGY_REQ',
    FileNumber: '13PIL1:cam1:FileNumber',
    WAXS2Theta: 'SR13ID01HU02IOC01:WAX_TTH_MTR',
    Newport_Rot: 'SR13ID01:GI_1_Y',
    Chi: 'SR13ID01HU02IOC01:GSAX_CHI_MTR',
    Chi_Speed: 'SR13ID01HU02IOC01:GSAX_CHI_MTR.VELO',
    N_Points_S1: 'SR13ID01HU02IOC02:scan1.NPTS',
    Det_Delay_S1: 'SR13ID01HU02IOC02:scan1.DDLY',
    Int_Tune: 'SR13ID01:DCM_P2_TUNE_AFTER_ENERGY_ENABLE',
    GI_1_OMG: 'SR13ID01:GI_1_OMG',
    GI_1_X: 'SR13ID01:GI_1_X',
    GI_1_Y: 'SR13ID01:GI_1_Y',
    AXTL: 'SR13ID01:GI_1_AXTL',
    TransDet: 'SR13ID01HU02IOC01:TR_MIRR_MTR',
    Slit1HSize: 'SR13ID01SLM01:X_SIZE_SP',
    Slit4HSize: 'SR13ID01SLM04:X_SIZE_SP',
    Slit4VSize: 'SR13ID01SLM04:Y_SIZE_SP',
    LynchInnerY: 'SR13ID01:AXIS3_VAL',
    LynchOuterY: 'SR13ID01:AXIS2_VAL',
    LynchX: 'SR13ID01:AXIS1_VAL',
    SyringePump1: 'SR13ID01HU02IOC01:SYR_PMP_1_MTR',
    SyringePump2: 'SR13ID01HU02IOC01:SYR_PMP_2_MTR',
    None: ''
};
var detectorStruct = {
    'WAXSROI1': '13PIL2:Stats1:Total_RBV',
    'WAXSROI2': '13PIL2:Stats2:Total_RBV',
    'WAXSROI3': '13PIL2:Stats3:Total_RBV',
    'Scaler5': 'SR13ID01HU02IOC02:scaler1.S5',
    'Scaler4': 'SR13ID01HU02IOC02:scaler1.S4',
    'Scaler2': 'SR13ID01HU02IOC02:scaler1.S2'
};
var detectorTrigStruct = {
    'Acquire': 'SR13ID01PYSEQ01:Acquire_CMD',
    'Scan1': 'SR13ID01HU02IOC02:scan1.EXSC',
    'Scan2': 'SR13ID01HU02IOC02:scan2.EXSC',
    'Scan3': 'SR13ID01HU02IOC02:scan3.EXSC',
    'Scaler': 'SR13ID01HU02IOC02:scaler1.CNT',
    'Pil1M_Acquire': '13PIL1:cam1:Acquire',
    'Pil200k_Acquire': '13PIL1:cam2:Acquire',
};
var positionerTestStruct = {
    SampleTableX: 'SMTEST:SMPL_TBL_X_MTR',
    SampleTableY: 'SMTEST:SMPL_TBL_Y_MTR',
    Omega: 'SMTEST:GSAX_OMG_MTR',
    FakeTemperature: '',
    None: ''
};
var detectorTestStruct = {
    'WAXSROI1': '13PIL2:Stats1:Total_RBV',
    'WAXSROI2': '13PIL2:Stats2:Total_RBV',
    'WAXSROI3': '13PIL2:Stats3:Total_RBV',
    'Scaler4': 'SR13ID01HU02IOC02:scaler1.S4'
};
var detectorTrigTestStruct = {
    'SMTESTCAM': 'SMTEST:cam1:Acquire',
    'Scan1': 'SMTEST:scan1.EXSC',
    'Scan2': 'SMTEST:scan2.EXSC',
    'Scan3': 'SMTEST:scan3.EXSC'
};
